# -*- coding: utf-8 -*-
"""
_astro.py —— 节气时刻 / 真太阳时（纯标准库，运行时零依赖）

设计原则：**能查表就不手算**。

1. 节气时刻：读 scripts/data/solar_terms_1900_2052.csv
   —— 该表由 JPL DE421 星历（经 Skyfield）预计算，格式为
      「每年 24 个节气 = 该年 1 月 1 日 00:00 起的分钟数（北京时间）」。
      生成脚本与口径见 scripts/_tools/gen_solar_terms.py，
      与 2026 年日本国立天文台《暦要項》及国内万年历对校，吻合到 1 分钟内。
      ✅ 1900–2052 年内直接查表，**不依赖任何近似天文公式**。

2. 超出 1900–2052：退回 Standish/Astronomical-Almanac 简化太阳黄经公式
   （文档标注精度约 0.01°，换算成时间约 ±15 分钟），
   调用方会显式打印「近似值」警告，绝不冒充精确值。

3. 真太阳时：经度时差 + 均时差（EOT 用常用近似式，年较差约 ±0.6 分钟）。
"""

import csv
import math
import os
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "data", "solar_terms_1900_2052.csv")

TERMS = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
         "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
         "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]

TERM_DEGREE = {"小寒": 285, "大寒": 300, "立春": 315, "雨水": 330,
               "惊蛰": 345, "春分": 0, "清明": 15, "谷雨": 30,
               "立夏": 45, "小满": 60, "芒种": 75, "夏至": 90,
               "小暑": 105, "大暑": 120, "立秋": 135, "处暑": 150,
               "白露": 165, "秋分": 180, "寒露": 195, "霜降": 210,
               "立冬": 225, "小雪": 240, "大雪": 255, "冬至": 270}

# 十二「节」（非中气）—— 起月、起大运均以此为准，08 A2 / A6
JIE = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
       "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]

# 节 -> 月支（寅月起，08 A2）
JIE_TO_ZHI = {"立春": "寅", "惊蛰": "卯", "清明": "辰", "立夏": "巳",
              "芒种": "午", "小暑": "未", "立秋": "申", "白露": "酉",
              "寒露": "戌", "立冬": "亥", "大雪": "子", "小寒": "丑"}

MIN_YEAR, MAX_YEAR = 1900, 2052

# ---------------------------------------------------------------- 数据表

_TABLE = None
_TABLE_WARNED = set()


def _load_table():
    global _TABLE
    if _TABLE is not None:
        return _TABLE
    if not os.path.exists(DATA_FILE):
        raise RuntimeError(
            "找不到节气数据表：%s\n可用 scripts/_tools/gen_solar_terms.py 重新生成 "
            "（需 pip install skyfield 与 DE421 星历）。" % DATA_FILE)
    table = {}
    with open(DATA_FILE, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        names = header[1:]
        for row in reader:
            year = int(row[0])
            table[year] = {names[i]: int(row[i + 1]) for i in range(len(names))}
    _TABLE = table
    return table


def table_source_note():
    return "节气时刻取自 JPL DE421 星历预计算表（1900–2052，北京时间）"


# ---------------------------------------------------------------- 节气

def terms_of_year(year: int):
    """返回 {节气名: datetime(北京时间)}"""
    if MIN_YEAR <= year <= MAX_YEAR:
        row = _load_table().get(year)
        if row is None:
            raise ValueError("缺年：%s" % year)
        base = datetime(year, 1, 1)
        return {k: base + timedelta(minutes=v) for k, v in row.items()}
    # 越界：近似
    if year not in _TABLE_WARNED:
        _TABLE_WARNED.add(year)
    return _approx_terms_of_year(year)


def is_approx_year(year: int) -> bool:
    return not (MIN_YEAR <= year <= MAX_YEAR)


def term_datetime(year: int, name: str) -> datetime:
    return terms_of_year(year)[name]


def all_terms_around(dt: datetime, span: int = 1):
    """返回 dt 前后若干年的全部节气，按时间排序 [(name, datetime), ...]"""
    out = []
    for y in range(dt.year - span, dt.year + span + 1):
        try:
            row = terms_of_year(y)
        except (ValueError, RuntimeError):
            continue
        for name, t in row.items():
            out.append((name, t))
    out.sort(key=lambda x: x[1])
    return out


def nearest_jie(dt: datetime):
    """返回 (上一个节名称+时刻, 下一个节名称+时刻)。只认「节」，不认中气。"""
    prev = nxt = None
    for name, t in all_terms_around(dt, span=1):
        if name not in JIE:
            continue
        if t <= dt:
            if prev is None or t > prev[1]:
                prev = (name, t)
        elif nxt is None or t < nxt[1]:
            nxt = (name, t)
    if prev is None or nxt is None:
        raise ValueError("无法定位节气，日期可能超出可用范围：%s" % dt)
    return prev, nxt


def current_jie(dt: datetime):
    """dt 所在月令的「节」(名称, 时刻, 月支)"""
    prev, _ = nearest_jie(dt)
    return prev[0], prev[1], JIE_TO_ZHI[prev[0]]


# ---------------------------------------------------------------- 近似回退（越界年份用）

def _apparent_sun_longitude(jd_ut: float) -> float:
    """Standish / AA 简化太阳视黄经（度）。精度约 0.01°≈±15 分钟时间。"""
    jd = jd_ut + _delta_t_approx(jd_ut) / 86400.0
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = math.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M)
         + 0.000289 * math.sin(3 * M))
    omega = math.radians(125.04 - 1934.136 * T)
    return (L0 + C - 0.00569 - 0.00478 * math.sin(omega)) % 360


def _delta_t_approx(jd_ut: float) -> float:
    y = 2000 + (jd_ut - 2451545.0) / 365.25
    return 62.92 + 0.32217 * (y - 2000) + 0.005589 * (y - 2000) ** 2


# 各节气的通常所在日期，作为近似搜索的中心点
_APPROX_CENTER = {
    "小寒": (1, 6), "大寒": (1, 20), "立春": (2, 4), "雨水": (2, 19),
    "惊蛰": (3, 6), "春分": (3, 21), "清明": (4, 5), "谷雨": (4, 20),
    "立夏": (5, 6), "小满": (5, 21), "芒种": (6, 6), "夏至": (6, 21),
    "小暑": (7, 7), "大暑": (7, 23), "立秋": (8, 8), "处暑": (8, 23),
    "白露": (9, 8), "秋分": (9, 23), "寒露": (10, 8), "霜降": (10, 23),
    "立冬": (11, 7), "小雪": (11, 22), "大雪": (12, 7), "冬至": (12, 21),
}

_JD_EPOCH = datetime(2000, 1, 1, 12)   # JD 2451545.0


def _jd_of(dt_ut):
    return 2451545.0 + (dt_ut - _JD_EPOCH).total_seconds() / 86400.0


def _dt_of_jd(jd_ut):
    return _JD_EPOCH + timedelta(days=jd_ut - 2451545.0)


def _approx_terms_of_year(year: int):
    """越界年份的近似节气（误差可达十余分钟，调用方会显式标注）。"""
    out = {}
    for name in TERMS:
        m, d = _APPROX_CENTER[name]
        center = datetime(year, m, d)
        target = TERM_DEGREE[name]
        lo = _jd_of(center - timedelta(days=25))
        hi = _jd_of(center + timedelta(days=25))
        for _ in range(90):
            mid = (lo + hi) / 2
            diff = (_apparent_sun_longitude(mid) - target) % 360
            if diff > 180:
                diff -= 360
            if diff < 0:
                lo = mid
            else:
                hi = mid
        jd = (lo + hi) / 2
        # 注意：_apparent_sun_longitude() 内部已自行把 UT 加 ΔT 转成 TT 再算黄经，
        # 二分求得的 jd 是 **UT**，此处只做 UT → 北京时（+8h），不可再减一次 ΔT。
        out[name] = _dt_of_jd(jd + 8 / 24.0)
    return out


# ---------------------------------------------------------------- 真太阳时

def equation_of_time(dt: datetime) -> float:
    """均时差（分钟）。常用近似式，全年误差约 ±0.6 分钟。"""
    N = dt.timetuple().tm_yday + (dt.hour - 12) / 24.0
    B = 2 * math.pi * (N - 81) / 364.0
    return 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)


def true_solar_time(dt: datetime, lon: float):
    """北京时间 + 经度时差 + 均时差。
    返回 (真太阳时 datetime, 经度时差分钟, 均时差分钟)"""
    lon_corr = (lon - 120.0) * 4.0
    eot = equation_of_time(dt)
    return dt + timedelta(minutes=lon_corr + eot), lon_corr, eot


# ---------------------------------------------------------------- 城市经度（近似）

CITY_LON = {
    "北京": 116.41, "上海": 121.47, "广州": 113.26, "深圳": 114.06,
    "天津": 117.20, "重庆": 106.55, "成都": 104.07, "杭州": 120.15,
    "南京": 118.78, "武汉": 114.31, "西安": 108.94, "沈阳": 123.43,
    "长春": 125.32, "哈尔滨": 126.53, "济南": 117.00, "青岛": 120.38,
    "郑州": 113.63, "长沙": 113.00, "南昌": 115.89, "合肥": 117.28,
    "福州": 119.30, "厦门": 118.09, "昆明": 102.71, "贵阳": 106.63,
    "南宁": 108.32, "海口": 110.32, "兰州": 103.83, "西宁": 101.78,
    "银川": 106.27, "乌鲁木齐": 87.62, "拉萨": 91.11, "呼和浩特": 111.75,
    "太原": 112.55, "石家庄": 114.51, "大连": 121.62, "宁波": 121.55,
    "苏州": 120.59, "温州": 120.70, "无锡": 120.30, "台北": 121.56,
    "香港": 114.17, "澳门": 113.55, "台北县": 121.45, "高雄": 120.30,
}

MISSING = object()


def resolve_lon(city=None, lon=None):
    """解析出生地经度。返回 (经度, 说明文本)"""
    if lon is not None:
        return float(lon), "经度 %.2f°（用户给定）" % float(lon)
    if city:
        hits = {k: v for k, v in CITY_LON.items() if city in k}
        if hits:
            k = sorted(hits)[0]
            return hits[k], "城市「%s」近似经度 %.2f°（市区中心，仅供校正参考）" % (k, hits[k])
        raise ValueError("内置城市表无「%s」，请用 --lon 直接给经度。" % city)
    return 120.0, "未给出生地经度，按东经 120°（即不做经度校正）处理"


if __name__ == "__main__":
    print(table_source_note())
    for y in (1990, 2001, 2026):
        for t in ("立春", "清明", "立夏", "冬至"):
            print(y, t, term_datetime(y, t).strftime("%Y-%m-%d %H:%M"))
    d = datetime(1990, 4, 12, 10, 30)
    t, lc, e = true_solar_time(d, 116.41)
    print("北京真太阳时:", t, "经度差", round(lc, 1), "均时差", round(e, 1))
