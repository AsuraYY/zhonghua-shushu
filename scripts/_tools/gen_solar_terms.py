# -*- coding: utf-8 -*-
"""
生成脚本（开发期用，不在 skill 运行时调用）：
    用 JPL DE421 星历（经 Skyfield 读取）计算二十四节气时刻，
    输出 scripts/data/solar_terms_1900_2053.csv。

算法口径：
    取「太阳视黄经」（apparent geocentric ecliptic longitude，含光行差与章动，
    基准为当日真分点）达到节气度数之时刻，二分逼近至 1e-9 日（<0.1 秒）；
    再按 ΔT（TT − UT1，历史常用取值线性插值）折算为
    北京时间（UTC+8）的「年内分钟数」。这也是现代万年历所用口径。

覆盖范围受限于所用星历：DE421 覆盖 1899-07-29 ~ 2053-10-09，
故本表取完整年份 **1900–2052**；2053 年之后由 scripts/_astro.py 走近似公式并显式标注。

运行：
    DE421_BSP=<path/to/de421.bsp> <python> scripts/_tools/gen_solar_terms.py
依赖（仅本生成脚本需要）：pip install skyfield numpy
"""

import csv
import os
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
OUT = os.path.join(SCRIPTS, "data", "solar_terms_1900_2052.csv")

YEAR_FROM, YEAR_TO = 1900, 2052
TZ_HOURS = 8  # 北京时间

TERMS = [
    ("小寒", 285), ("大寒", 300), ("立春", 315), ("雨水", 330),
    ("惊蛰", 345), ("春分", 0), ("清明", 15), ("谷雨", 30),
    ("立夏", 45), ("小满", 60), ("芒种", 75), ("夏至", 90),
    ("小暑", 105), ("大暑", 120), ("立秋", 135), ("处暑", 150),
    ("白露", 165), ("秋分", 180), ("寒露", 195), ("霜降", 210),
    ("立冬", 225), ("小雪", 240), ("大雪", 255), ("冬至", 270),
]

# ΔT = TT − UT1（秒），历史常用值；中间年份线性插值。1900 年后应精确到 1 秒内。
DELTA_T_ANCHORS = [
    (1900, -2.7), (1910, 10.4), (1920, 21.2), (1930, 24.0), (1940, 24.3),
    (1950, 29.2), (1960, 33.1), (1970, 40.2), (1980, 50.5), (1990, 56.9),
    (2000, 63.8), (2010, 66.8), (2020, 69.4), (2030, 72.0), (2040, 75.0),
    (2050, 78.6),
]


def delta_t(year):
    pts = DELTA_T_ANCHORS
    y = float(year)
    if y <= pts[0][0]:
        return pts[0][1]
    for i in range(1, len(pts)):
        y0, v0 = pts[i - 1]
        y1, v1 = pts[i]
        if y0 <= y <= y1:
            return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
    return pts[-1][1]


def load_planets():
    import skyfield.api as api
    candidates = [
        os.environ.get("DE421_BSP", ""),
        os.path.join(HERE, "de421.bsp"),
        os.path.join(SCRIPTS, "data", "de421.bsp"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            print("使用本地星历：", p)
            return api.load_file(p)
    print("本地无 de421.bsp，尝试联网下载…（约 17MB）")
    return api.load("de421.bsp")


def main():
    import numpy as np
    import skyfield.api as api

    planets = load_planets()
    ts = api.load.timescale()
    earth, sun = planets["earth"], planets["sun"]

    def app_lon(jd_tt):
        """太阳视黄经（度）。支持标量或 numpy 数组。"""
        if isinstance(jd_tt, float):
            jd_tt = np.array([jd_tt])
        arr = np.atleast_1d(np.asarray(jd_tt, dtype=float))
        t = ts.tt_jd(arr)
        lat, lon, _r = earth.at(t).observe(sun).apparent().ecliptic_latlon(epoch="date")
        out = np.mod(lon.degrees, 360.0)
        return out if out.size > 1 else float(out[0])

    def jd_of(y, m, d):
        return 2451545.0 + (datetime(y, m, d, 12) - datetime(2000, 1, 1, 12)).total_seconds() / 86400.0

    # 1) 粗扫：整个区间 1 天步长
    jd0 = jd_of(YEAR_FROM, 1, 1) - 2
    jd1 = jd_of(YEAR_TO, 12, 31)      # 覆盖本年全部节气，且不越过星历期限
    grid = np.arange(jd0, jd1, 1.0)
    print("粗扫 %d 个采样点…" % grid.size)
    lon_grid = app_lon(grid)

    # 2) 找每个目标度数的所有跨越点
    results = {}   # (year, term) -> minute of year
    for name, deg in TERMS:
        d0 = np.mod(lon_grid[:-1] - deg, 360.0)
        d0 = np.where(d0 > 180, d0 - 360, d0)
        d1 = np.mod(lon_grid[1:] - deg, 360.0)
        d1 = np.where(d1 > 180, d1 - 360, d1)
        mask = (d0 < 0) & (d1 >= 0)
        idx = np.nonzero(mask)[0]
        lo = grid[idx].copy()
        hi = grid[idx + 1].copy()
        # 3) 矢量二分（40 轮 -> ~1e-12 日）
        for _ in range(45):
            mid = (lo + hi) / 2
            f = np.mod(app_lon(mid) - deg, 360.0)
            f = np.where(f > 180, f - 360, f)
            left = f < 0
            lo = np.where(left, mid, lo)
            hi = np.where(left, hi, mid)
        jd_hit = (lo + hi) / 2
        for j in jd_hit:
            years_frac = 2000 + (j - 2451545.0) / 365.25
            dt_bj = datetime(2000, 1, 1, 12) + timedelta(
                days=j - 2451545.0 - delta_t(years_frac) / 86400.0 + TZ_HOURS / 24.0)
            y = dt_bj.year
            if YEAR_FROM <= y <= YEAR_TO:
                # 取整到最近的分钟（与通书/万年历发布口径一致）
                results[(y, name)] = int(round((dt_bj - datetime(y, 1, 1)).total_seconds() / 60.0))
        print("  %s：%d 个" % (name, jd_hit.size))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year"] + [t[0] for t in TERMS])
        for y in range(YEAR_FROM, YEAR_TO + 1):
            row = [y]
            missing = []
            for name, _deg in TERMS:
                v = results.get((y, name))
                if v is None:
                    missing.append(name)
                    v = ""
                row.append(v)
            if missing:
                print("⚠️ %d 年缺：%s" % (y, ",".join(missing)))
            w.writerow(row)
    print("已写出：", OUT)

    # 抽检
    print("\n抽检（北京时间）：")
    for probe in (1912, 1949, 1990, 2001, 2026, 2050):
        for want in ("立春", "清明", "立夏", "冬至"):
            v = results.get((probe, want))
            if v is None:
                continue
            dt = datetime(probe, 1, 1) + timedelta(minutes=v)
            print("  %d %s = %s" % (probe, want, dt.strftime("%m-%d %H:%M")))


if __name__ == "__main__":
    main()
