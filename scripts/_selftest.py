#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
_selftest.py —— 脚本层自检（开发/升级后必跑）

依赖：仅标准库。运行：
    <python> scripts/_selftest.py

校验内容：
  A. 干支锚点（1949-10-01 甲子 / 2000-01-01 戊午 / 2024-02-10 甲辰）
  B. 节气表：2026 年二十四节气 vs 日本国立天文台《暦要項》+国内万年历
  C. 五虎遁 / 五鼠遁 / 旬空 / 纳音
  D. 八卦与六十四卦：由八宫表推导的正确性 + 02-zhanbu.md 案例「水雷屯」装卦全表
  E. 梅花案例：02-zhanbu.md「报数 3、8」-> 火地晋 / 体坤用离 / 用水山蹇 / 变天地否
  F. 八字案例：08-algorithms.md「1990-04-12 10:30」-> 庚午 庚辰 丁未 乙巳，
     男命起运 7岁10月、女命 2岁4月
  G. 五格：08 G 节算法
"""

import sys
from datetime import datetime

import _common as C
import _astro
import _bagua as B
import bazi
import meihua
import wuge

FAILS = []
PASSES = 0


def check(label, got, want):
    global PASSES
    ok = (got == want) if not callable(want) else want(got)
    if ok:
        PASSES += 1
        print("  ✅ %-46s %s" % (label, got))
    else:
        FAILS.append(label)
        print("  ❌ %-46s 得到 %r，期望 %r" % (label, got, want))


def sec(title):
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


def main():
    sec("A. 干支锚点（08 A3 三点交叉校验）")
    check("1949-10-01 日柱", C.day_ganzhi(1949, 10, 1), "甲子")
    check("2000-01-01 日柱", C.day_ganzhi(2000, 1, 1), "戊午")
    check("2024-02-10 日柱", C.day_ganzhi(2024, 2, 10), "甲辰")
    check("2000-01-07 锚点", C.day_ganzhi(2000, 1, 7), "甲子")
    check("2026-10-15 壬戌（外部核验）", C.day_ganzhi(2026, 10, 15), "壬戌")

    sec("B. 2026 年节气（秒级对照公开万年历，容差 ±60 秒）")
    # 参照来源①：公开万年历 2026 节气表（精确到秒）
    ref_sec = {
        "立春": "2026-02-04 04:01:51", "雨水": "2026-02-18 23:51:39",
        "惊蛰": "2026-03-05 21:58:43", "春分": "2026-03-20 22:45:42",
        "清明": "2026-04-05 02:39:43", "谷雨": "2026-04-20 09:38:51",
        "立夏": "2026-05-05 19:48:27", "小满": "2026-05-21 08:36:28",
        "芒种": "2026-06-05 23:48:04", "夏至": "2026-06-21 16:24:12",
        "小暑": "2026-07-07 09:56:40", "大暑": "2026-07-23 03:12:48",
        "立秋": "2026-08-07 19:42:26", "处暑": "2026-08-23 10:18:31",
        "白露": "2026-09-07 22:40:59", "秋分": "2026-09-23 08:04:56",
        "寒露": "2026-10-08 14:28:59", "霜降": "2026-10-23 17:37:39",
        "立冬": "2026-11-07 17:51:46", "小雪": "2026-11-22 15:23:03",
        "大雪": "2026-12-07 10:52:14", "冬至": "2026-12-22 04:49:55",
    }
    # 参照来源②：日本国立天文台《暦要項》令和8年（JST 整分值，减 1h 为北京时）
    ref_min = {
        "小寒": "2026-01-05 16:23", "大寒": "2026-01-20 09:45",
    }
    worst, worst_name = 0.0, ""
    for name, want in ref_sec.items():
        got = _astro.term_datetime(2026, name)
        want_dt = datetime.strptime(want, "%Y-%m-%d %H:%M:%S")
        diff = abs((got - want_dt).total_seconds())
        worst, worst_name = (diff, name) if diff > worst else (worst, worst_name)
        if diff > 60:
            print("  ❌ %s 得到 %s，参照① %s，差 %.0f 秒"
                  % (name, got.strftime("%m-%d %H:%M"), want_dt.strftime("%m-%d %H:%M:%S"), diff))
    for name, want in ref_min.items():
        got = _astro.term_datetime(2026, name)
        want_dt = datetime.strptime(want, "%Y-%m-%d %H:%M")
        diff = abs((got - want_dt).total_seconds())
        worst, worst_name = (diff, name) if diff > worst else (worst, worst_name)
        if diff > 90:
            print("  ❌ %s 得到 %s，参照② %s，差 %.0f 秒"
                  % (name, got.strftime("%m-%d %H:%M"), want_dt.strftime("%m-%d %H:%M"), diff))
    print("  对照 24 个节气：与公开发布值最大偏差 %.0f 秒（%s）" % (worst, worst_name or "无"))
    if worst <= 60:
        print("  ✅ 全部落在 ±60 秒内（表内已四舍五入到分钟，故最小单位即 60 秒）")
        globals()["PASSES"] += 1
    else:
        FAILS.append("节气表对照")

    sec("C. 五虎遁 / 五鼠遁 / 旬空 / 纳音")
    check("庚午年辰月（08 A2 实测）", C.month_ganzhi("庚", "辰"), "庚辰")
    check("丁未日巳时（08 A4 实测）", C.wushu_dun("丁", "巳") + "巳", "乙巳")
    check("甲辰旬空", C.xunkong("甲辰"), ("寅", "卯"))
    check("甲午旬空", C.xunkong("甲午"), ("辰", "巳"))
    check("甲申旬空", C.xunkong("甲申"), ("午", "未"))
    check("庚午纳音", C.na_yin("庚午"), ("路旁土", "土"))
    check("甲子纳音", C.na_yin("甲子"), ("海中金", "金"))
    check("壬戌纳音", C.na_yin("壬戌"), ("大海水", "水"))

    sec("D. 六十四卦（由八宫表推导，非手工录入）")
    check("卦表条目数", len(B.GUA64), 64)
    tunitmap_found = False
    for g in B.GUA64.values():
        if g["name"] == "大有":
            check("火天大有 卦宫/世/应", (g["palace"], g["shi"], g["ying"]), ("乾", 3, 6))
            tunitmap_found = True
    check("乾->姤->遁->否->观->剥->晋->大有 存在", tunitmap_found, True)
    check("乾为天 世/应", (B.gua_of_name("乾")["shi"], B.gua_of_name("乾")["ying"]), (6, 3))

    print("  【案例对照】02-zhanbu.md「水雷屯」变「风雷益」")
    lines = [(1, 0), (0, 0), (0, 0), (0, 0), (1, 0), (0, 1)]
    info, rows = B.zhuang_gua(lines)
    check("  本卦名/卦宫/卦宫五行", (info["name"], info["palace"], info["palace_wx"]),
          ("屯", "坎", "水"))
    check("  几世卦", info["gen"], "二世")
    check("  世爻/应爻", (info["shi"], info["ying"]), (2, 5))
    check("  上卦/下卦", (info["upper"], info["lower"]), ("坎", "震"))
    expect = [("庚子", "兄弟", False), ("庚寅", "子孙", False), ("庚辰", "官鬼", False),
              ("戊申", "父母", False), ("戊戌", "官鬼", False), ("戊子", "兄弟", True)]
    got = [(r["ganzhi"], r["liuqin"], r["moving"]) for r in rows]
    check("  六爻纳干支/六亲/动静 全表", got, expect)
    check("  变卦", B.bian_gua(lines)["name"], "益")
    check("  互卦", B.hu_gua(lines)["name"], "剥")

    sec("E. 梅花易数（02-zhanbu.md 案例：报数 3、8）")
    r = meihua.build("离", "坤", 5)
    check("本卦 火地晋", r["ben_gua"]["name"], "晋")
    check("动爻在五爻 → 上卦为用", (r["ti"], r["yong"]), ("坤", "离"))
    check("体坤(土) 用离(火) → 用生体", r["relation"], "用生体")
    check("互卦 水山蹇", r["hu_gua"]["name"], "蹇")
    check("变卦 天地否", r["bian_gua"]["name"], "否")
    shang, _ = meihua.shu_to_gua(3)
    xia, _ = meihua.shu_to_gua(8)
    check("先天数 3=离、8=坤", (shang, xia), ("离", "坤"))
    check("先天数 5=巽、6=坎（易错点）",
          (meihua.shu_to_gua(5)[0], meihua.shu_to_gua(6)[0]), ("巽", "坎"))
    check("动爻 (3+8) mod 6 = 5", meihua.dong_yao(3 + 8), 5)

    sec("F. 八字（08-algorithms.md 实测案例 1990-04-12 10:30）")
    dt = datetime(1990, 4, 12, 10, 30)
    info = bazi.build_chart(dt, "male", 120.0, use_solar_time=False)
    check("四柱", (info["year_gz"], info["month_gz"], info["day_gz"], info["hour_gz"]),
          ("庚午", "庚辰", "丁未", "乙巳"))
    check("月支（清明后、立夏前）", info["jie"]["zhi"], "辰")
    check("日主的十神：月干庚（阳金）被丁火克且异阴阳", C.shi_shen("丁", "庚"), "正财")
    check("日主的十神：时干乙=偏印", C.shi_shen("丁", "乙"), "偏印")
    # 起运（08 A6 实测：男 7岁10月 / 女 2岁4月）
    male = bazi.build_chart(dt, "male", 120.0, use_solar_time=False)
    female = bazi.build_chart(dt, "female", 120.0, use_solar_time=False)
    check("男命顺行", male["dayun"]["forward"], True)
    check("女命逆行", female["dayun"]["forward"], False)
    check("男命起运（08 记 7岁10月）", male["dayun"]["qiyun_text"], "7岁10月")
    check("女命起运（08 记 2岁4月）", female["dayun"]["qiyun_text"], "2岁4月")
    check("大运首运（顺行辛巳）", male["dayun"]["list"][0]["ganzhi"], "辛巳")
    check("大运首运（逆行己卯）", female["dayun"]["list"][0]["ganzhi"], "己卯")

    sec("G. 五格剖象（08 G）")
    r5 = wuge.calc([11], [8, 7])
    check("天格（单姓=姓+1）", r5["tian"], 12)
    check("人格（姓末+名首）", r5["ren"], 19)
    check("地格（复名之和）", r5["di"], 15)
    check("总格（全部之和）", r5["zong"], 26)
    check("外格（总格-人格）", r5["wai"], 7)

    sec("结果")
    print("  通过 %d 项，失败 %d 项" % (PASSES, len(FAILS)))
    if FAILS:
        print("  失败项：")
        for f in FAILS:
            print("    - " + f)
        return 1
    print("  🎉 全部通过：脚本层输出可直接作为盘面依据。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
