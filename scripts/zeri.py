#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zeri.py —— 择日/历法干支速查（纯标准库）

用法：
    python zeri.py --date 2026-10-16
    python zeri.py --from 2026-11-01 --to 2026-11-30
    python zeri.py --date 2026-10-16 --avoid-zhi 午        # 看与某生肖支是否犯冲

输出内容（均为可机械推导项）：
    公历 / 星期 / 日干支 / 日支生肖 / 日纳音 / 旬空 / 节气月建 / 建除十二神
    / 六冲生肖提示

刻意不输出的东西（避免制造"表看起来很全"的假象）：
    ① 黄黑道十二神：起例版本互相矛盾（"子午月起申/寅申月起子"与
       "建日为青龙"口诀两套并存），故不在脚本中实现，请查通书。
    ② 二十八宿：需依赖绝对锚点，且各版本相位不同，不予计算。
    ③ 宜忌、吉凶：属宜忌表范畴，本 skill 不内置宜忌表。
以上均在 08-algorithms.md E / F 节有同样说明。
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

import _astro
import _common as C

SHENG_XIAO = {"子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔", "辰": "龙", "巳": "蛇",
              "午": "马", "未": "羊", "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪"}

# 建除十二神（顺序固定，08 E）
JIAN_CHU = ["建", "除", "满", "平", "定", "执", "破", "危", "成", "收", "开", "闭"]

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def day_info(d: datetime):
    gz = C.day_ganzhi(dt=d.date())
    gan, zhi = gz[0], gz[1]
    jie_name, _jie_dt, month_zhi = _astro.current_jie(d)
    jc_index = (C.ZHI_INDEX[zhi] - C.ZHI_INDEX[month_zhi]) % 12
    chong_branch = None
    for a, b in C.LIU_CHONG:
        if a == zhi:
            chong_branch = b
        if b == zhi:
            chong_branch = a
    he_branch = None
    for a, b in C.LIU_HE:
        if a == zhi:
            he_branch = b
        if b == zhi:
            he_branch = a
    return {
        "date": d.strftime("%Y-%m-%d"),
        "weekday": WEEKDAY_CN[d.weekday()],
        "day_ganzhi": gz,
        "day_wx": C.ZHI_WU_XING[zhi],
        "shengxiao": SHENG_XIAO[zhi],
        "nayin": C.na_yin(gz),
        "xunkong": C.xunkong(gz),
        "month_zhi": month_zhi,
        "month_jie": jie_name,
        "jianchu": JIAN_CHU[jc_index],
        "chong_branch": chong_branch,
        "chong": SHENG_XIAO[chong_branch] if chong_branch else None,
        "liuhe": SHENG_XIAO[he_branch] if he_branch else None,
        "approx": _astro.is_approx_year(d.year),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="择日/历法干支速查")
    p.add_argument("--date", help="单日查询 YYYY-MM-DD")
    p.add_argument("--from", dest="dfrom", help="区间起日")
    p.add_argument("--to", dest="dto", help="区间止日")
    p.add_argument("--avoid-zhi", help="给出需避开的生肖支（看当日是否冲之）")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    dates = []
    if a.date:
        dates = [C.parse_datetime(a.date)]
    elif a.dfrom and a.dto:
        d0 = C.parse_datetime(a.dfrom)
        d1 = C.parse_datetime(a.dto)
        d = d0
        while d <= d1:
            dates.append(d)
            d += timedelta(days=1)
    else:
        p.error("请给 --date 或 --from/--to")

    rows = [day_info(d) for d in dates]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print("=" * 78)
    print("历法/择日速查（脚本输出）　%s" % _astro.table_source_note())
    print("=" * 78)
    hdr = "%-12s %-4s %-6s %-8s %-10s %-8s %-6s %-5s %s"
    print(hdr % ("日期", "星期", "日干支", "生肖", "纳音", "月建", "建除", "旬空", "冲"))
    print("-" * 78)
    for r in rows:
        flag = ""
        if a.avoid_zhi:
            if r["day_ganzhi"][1] == a.avoid_zhi:
                flag = " ← 当日支即所给生肖支"
            elif r["chong_branch"] == a.avoid_zhi:
                flag = " ← 冲%s（%s）" % (r["chong"], SHENG_XIAO[a.avoid_zhi])
        print(hdr % (r["date"], r["weekday"], r["day_ganzhi"],
                     r["shengxiao"], "%s(%s)" % (r["nayin"][0], r["nayin"][1]),
                     r["month_zhi"], r["jianchu"], "".join(r["xunkong"]),
                     (r["chong"] or "") + flag))
    print("-" * 78)
    print("月建按节气月（立春寅月起），非农历初一 —— 08 A2。")
    print("建除：日支与月支同者为「建」，其后顺推十二神。")
    print("未输出：黄黑道（起例版本矛盾）、二十八宿（需锚点）、宜忌表（本 skill 不内置）。")
    print("吉凶宜忌属民俗，请以通书与实际用事为准；本脚本只给历法数值。")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
