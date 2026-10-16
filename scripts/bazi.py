#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bazi.py —— 四柱八字排盘（纯标准库）

用法：
    python bazi.py --datetime "1990-04-12 10:30" --gender male
    python bazi.py --datetime "1993-11-08 09:15" --gender male --city 兰州 --lon 103.83
    python bazi.py --datetime "1990-04-12 10:30" --gender female --json
    python bazi.py --datetime "1990-04-12 10:30" --gender male --years 2026,2027

参数：
    --datetime   出生时间（默认按北京时间），格式 YYYY-MM-DD HH:MM
    --gender     male|female（决定大运顺逆）
    --lon        出生地东经度数（优先，推荐）
    --city       城市名（内置近似经度表，兜底用）
    --tz         时区偏移，默认 8（北京时间）
    --no-solar-time   不做真太阳时校正（默认做）
    --zishi      same|next，23:00-24:00 归当日 or 归次日，默认 next（现代通行）
    --years      需要一并列出流年干支的年份，逗号分隔
    --json       输出 JSON（供上层模型解析）

算法口径全部对齐 references/08-algorithms.md A 节：
    立春换年 / 节换月 + 五虎遁 / 儒略日定日柱 / 五鼠遁定时柱 / 三天折一岁起运
节气时刻查 JPL DE421 预计算表，不手算。
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

import _astro
import _common as C


def yun_index(i):
    return C.ganzhi(i)


def build_chart(dt_input, gender, lon, use_solar_time=True, zishi="next"):
    """排盘。返回 dict"""
    info = {"raw": dt_input, "gender": gender, "lon": lon}

    # 1. 真太阳时校正
    note_lon = ""
    if use_solar_time:
        dt_eff, lon_corr, eot = _astro.true_solar_time(dt_input, lon)
        info["correction"] = {"lon_corr_min": round(lon_corr, 2),
                              "eot_min": round(eot, 2),
                              "datetime": dt_eff}
    else:
        dt_eff, lon_corr, eot = dt_input, 0.0, 0.0
        info["correction"] = {"lon_corr_min": 0, "eot_min": 0, "datetime": dt_eff,
                              "skipped": True}
    info["effective_datetime"] = dt_eff

    # 2. 年柱（立春换年）
    approx_year = _astro.is_approx_year(dt_eff.year)
    lichun_here = _astro.term_datetime(dt_eff.year, "立春")
    ming_year = dt_eff.year if dt_eff >= lichun_here else dt_eff.year - 1
    if dt_eff < lichun_here:
        lichun_ref = lichun_here              # 本年立春尚未到
    year_idx = (ming_year - 4) % 60
    year_gz = C.ganzhi(year_idx)

    # 3. 月柱（节换月 + 五虎遁）
    jie_name, jie_dt, month_zhi = _astro.current_jie(dt_eff)
    month_gz = C.month_ganzhi(year_gz[0], month_zhi)

    # 4. 日柱（儒略日）+ 子时换日政策
    day_d = dt_eff.date()
    if dt_eff.hour >= 23 and zishi == "next":
        day_d = day_d + timedelta(days=1)
    day_gz = C.day_ganzhi(dt=day_d)

    # 5. 时柱（五鼠遁）
    hour_branch = C.hour_zhi(dt_eff.hour + dt_eff.minute / 60.0)
    hour_gz = C.wushu_dun(day_gz[0], hour_branch) + hour_branch

    ri_gan = day_gz[0]
    pillars = [
        ("年", year_gz), ("月", month_gz), ("日", day_gz), ("时", hour_gz),
    ]

    # 十神 / 藏干 / 纳音
    detail = []
    for tag, gz in pillars:
        is_self = (tag == "日")
        detail.append({
            "tag": tag,
            "ganzhi": gz,
            "gan": gz[0],
            "zhi": gz[1],
            "shishen": "〔日主〕" if is_self else C.shi_shen(ri_gan, gz[0]),
            "canggan": [{"gan": g, "shishen": C.shi_shen(ri_gan, g)}
                        for g in C.CANG_GAN[gz[1]]],
            "nayin": C.na_yin(gz),
        })

    xk = C.xunkong(day_gz)
    info.update({
        "lichun": lichun_here,
        "jie": {"name": jie_name, "datetime": jie_dt, "zhi": month_zhi},
        "year_gz": year_gz, "month_gz": month_gz, "day_gz": day_gz, "hour_gz": hour_gz,
        "pillars": pillars, "detail": detail,
        "xunkong": {"by_day": xk, "by_year": C.xunkong(year_gz)},
        "ri_gan": ri_gan,
        "approx": approx_year,
        "zishi_policy": zishi,
    })

    # 6. 大运
    prev_jie, next_jie = _astro.nearest_jie(dt_eff)
    yang_year = year_gz[0] in C.GAN_YANG
    forward = (yang_year and gender == "male") or ((not yang_year) and gender == "female")
    target_name, target_dt = (next_jie if forward else prev_jie)
    days = abs((target_dt - dt_eff).total_seconds()) / 86400.0
    start_dt = dt_eff + timedelta(days=days / 3.0 * 365.25)
    month_idx = C.parse_ganzhi(month_gz)
    dayun = []
    for i in range(1, 9):
        idx = (month_idx + i) if forward else (month_idx - i)
        dayun.append({
            "ganzhi": C.ganzhi(idx),
            "start_year": start_dt.year + (i - 1) * 10,
            "end_year": start_dt.year + i * 10,
            "start_age_text": C.days_to_age(days + (i - 1) * 30),
        })
    info["dayun"] = {
        "forward": forward,
        "rule": "阳年男/阴年女顺排；阴年男/阳年女逆排（以年干阴阳定）",
        "target_jie": {"name": target_name, "datetime": target_dt},
        "days_to_jie": round(days, 3),
        "qiyun_text": C.days_to_age(days),
        "qiyun_start_date": start_dt.strftime("%Y-%m-%d"),
        "list": dayun,
    }
    return info


def year_ganzhi_of_year(y):
    return C.ganzhi((y - 4) % 60)


def print_chart(info, years=None):
    dt_eff = info["effective_datetime"]
    line = "=" * 60
    print(line)
    print("四柱八字排盘（脚本输出，勿再手工加改动）")
    print(line)
    print("输入      ：公历 %s  性别：%s  经度：%.2f°"
          % (info["raw"].strftime("%Y-%m-%d %H:%M"),
             "男" if info["gender"] == "male" else "女", info["lon"]))
    cr = info["correction"]
    if cr.get("skipped"):
        print("真太阳时  ：已关闭（--no-solar-time）")
    else:
        print("真太阳时  ：%s（经度时差 %+.1f 分，均时差 %+.1f 分）"
              % (dt_eff.strftime("%Y-%m-%d %H:%M"), cr["lon_corr_min"], cr["eot_min"]))
    print("立春      ：%s   %s立春"
          % (info["lichun"].strftime("%Y-%m-%d %H:%M"),
             "已过" if dt_eff >= info["lichun"] else "未到"))
    print("月令      ：%s节（%s）之后 → 月支 %s"
          % (info["jie"]["name"], info["jie"]["datetime"].strftime("%Y-%m-%d %H:%M"),
             info["jie"]["zhi"]))
    print("子时政策  ：23:00 后%s（%s）" %
          ("归次日" if info["zishi_policy"] == "next" else "归当日", info["zishi_policy"]))
    print(line)
    print("【四柱】")
    print("  " + "   ".join("%s柱" % d["tag"] for d in info["detail"]))
    print("  " + "   ".join(d["ganzhi"] for d in info["detail"]))
    print("  十神：" + " ".join("%s=%s" % (d["tag"], d["shishen"]) for d in info["detail"]))
    for d in info["detail"]:
        cg = "/".join("%s%s" % (x["gan"], x["shishen"]) for x in d["canggan"])
        print("  %s柱 %s：藏干 %s ；纳音 %s（%s）"
              % (d["tag"], d["ganzhi"], cg, d["nayin"][0], d["nayin"][1]))
    print("  日主：%s%s　旬空（日柱查）：%s%s"
          % (info["ri_gan"], C.GAN_WU_XING[info["ri_gan"]],
             info["xunkong"]["by_day"][0], info["xunkong"]["by_day"][1]))
    print(line)
    dy = info["dayun"]
    print("【大运】%s行（%s）" % ("顺" if dy["forward"] else "逆", dy["rule"]))
    print("  基准节  ：%s（%s）"
          % (dy["target_jie"]["name"], dy["target_jie"]["datetime"].strftime("%Y-%m-%d %H:%M")))
    print("  距该节  ：%.3f 天 → 三天折一岁 → 起运约 %s（约 %s 起）"
          % (dy["days_to_jie"], dy["qiyun_text"], dy["qiyun_start_date"]))
    for i, d in enumerate(dy["list"]):
        print("    %2d. %s　约 %s–%s" % (i + 1, d["ganzhi"], d["start_year"], d["end_year"]))
    if years:
        print(line)
        print("【流年干支】（立春后算当年）")
        for y in years:
            gz = year_ganzhi_of_year(y)
            lichun = _astro.term_datetime(y, "立春")
            print("  %s = %s（立春 %s），与日主关系：%s"
                  % (y, gz, lichun.strftime("%m-%d %H:%M"), C.shi_shen(info["ri_gan"], gz[0])))
    print(line)
    if info["approx"]:
        print("⚠️ 该年超出内建节气表（%d–%d），节气为**近似值**，误差可达十余分钟；"
              "凡节气边界附近的判断须提示用户以万年历核对。"
              % (_astro.MIN_YEAR, _astro.MAX_YEAR))
    print("复核来源：%s；日柱由儒略日推算（08 A3）" % _astro.table_source_note())
    print("以上为排盘数据，不含吉凶断言；解读请遵守 skill 的边界声明。")
    print(line)


def main(argv=None):
    p = argparse.ArgumentParser(description="四柱八字排盘")
    p.add_argument("--datetime", required=True, help='公历出生时间 "YYYY-MM-DD HH:MM"')
    p.add_argument("--gender", required=True, choices=["male", "female"])
    p.add_argument("--lon", type=float, default=None)
    p.add_argument("--city", default=None)
    p.add_argument("--tz", type=float, default=8.0)
    p.add_argument("--no-solar-time", action="store_true")
    p.add_argument("--zishi", default="next", choices=["same", "next"])
    p.add_argument("--years", default="", help="需要列出流年的年份，逗号分隔")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    dt = C.parse_datetime(a.datetime)
    lon, lon_note = _astro.resolve_lon(a.city, a.lon)
    if a.tz != 8.0:
        dt = dt - timedelta(hours=a.tz - 8.0)

    info = build_chart(dt, a.gender, lon, not a.no_solar_time, a.zishi)
    info["lon_note"] = lon_note

    years = [int(x) for x in a.years.split(",") if x.strip()]

    if a.json:
        def enc(obj):
            """递归清理：datetime → 文本，tuple → list"""
            if isinstance(obj, datetime):
                return obj.strftime("%Y-%m-%d %H:%M")
            if isinstance(obj, tuple):
                return [enc(x) for x in obj]
            if isinstance(obj, list):
                return [enc(x) for x in obj]
            if isinstance(obj, dict):
                return {k: enc(v) for k, v in obj.items()}
            return obj
        print(json.dumps(enc(info), ensure_ascii=False, indent=2))
    else:
        print_chart(info, years)
    return 0


if __name__ == "__main__":
    sys.exit(main())
