#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
meihua.py —— 梅花易数起卦（纯标准库）

用法：
    python meihua.py --numbers 3,8                # 两数起卦（08 C2）
    python meihua.py --numbers 3,8,5              # 三数变通：第三数并入动爻（非通行法，会标注）
    python meihua.py --time "2026-10-16 14:00" --lunar-month 8 --lunar-day 24
    python meihua.py --numbers 3,8 --json

说明：
    先天八卦数必用（乾1 兑2 离3 震4 **巽5 坎6** 艮7 坤8）—— 08 C1，勿用后天方位数。
    体用判定：**动爻所在之卦为用卦**，另一卦为体卦 —— 08 C4。
    时间起卦需农历月日，脚本不支持公历→农历换算，故须由使用者给出。
"""

import argparse
import json
import sys

import _bagua as B
import _common as C

XIU_SHU_NOTE = "先天八卦数（08 C1）"


def shu_to_gua(n):
    """数字 -> 卦（mod 8，余 0 作 8）"""
    r = n % 8
    if r == 0:
        r = 8
    return B.SHU_TO_TRIGRAM[r], r


def dong_yao(n):
    """动爻（mod 6，余 0 作第 6 爻）"""
    r = n % 6
    return 6 if r == 0 else r


def build(upper: str, lower: str, moving: int):
    up_lines = B.TRIGRAM_LINES[upper]
    low_lines = B.TRIGRAM_LINES[lower]
    lines = list(low_lines) + list(up_lines)      # 初..上
    bian = list(lines)
    bian[moving - 1] = 1 - bian[moving - 1]
    ben = B.gua_of_lines(lines)
    biangua = B.gua_of_lines(bian)
    hugua = B.hu_gua([(v, False) for v in lines])
    ti, yong = B.ti_yong(upper, lower, moving)
    rel, desc, ti_wx, yong_wx = B.ti_yong_relation(ti, yong)
    return {
        "upper": upper, "lower": lower, "moving": moving,
        "ben_gua": {"name": ben["name"], "upper": ben["upper"], "lower": ben["lower"]},
        "bian_gua": {"name": biangua["name"], "upper": biangua["upper"], "lower": biangua["lower"]},
        "hu_gua": {"name": hugua["name"], "upper": hugua["upper"], "lower": hugua["lower"]},
        "ti": ti, "yong": yong,
        "ti_wx": ti_wx, "yong_wx": yong_wx,
        "relation": rel, "relation_desc": desc,
        "ti_fangwei": B.HOU_TIAN_FANGWEI[ti],
        "yong_fangwei": B.HOU_TIAN_FANGWEI[yong],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="梅花易数起卦")
    p.add_argument("--numbers", help="起卦数字，逗号分隔（2 个为主，3 个为变通）")
    p.add_argument("--time", help='时间起卦用：公历 "YYYY-MM-DD HH:MM"')
    p.add_argument("--lunar-month", type=int, help="农历月（时间起卦必需）")
    p.add_argument("--lunar-day", type=int, help="农历日（时间起卦必需）")
    p.add_argument("--year-branch", help="年支，如「午」（不给则由出生日按立春推算）")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    variant = False
    if a.numbers:
        ns = [int(x) for x in a.numbers.replace("，", ",").split(",")]
        if len(ns) == 2:
            up, up_n = shu_to_gua(ns[0])
            low, low_n = shu_to_gua(ns[1])
            moving = dong_yao(ns[0] + ns[1])
        elif len(ns) == 3:
            up, up_n = shu_to_gua(ns[0])
            low, low_n = shu_to_gua(ns[1])
            moving = dong_yao(ns[0] + ns[1] + ns[2])
            variant = True
        else:
            p.error("--numbers 需 2 或 3 个数")
        source = "数字起卦：上卦=%d，下卦=%d，动爻由和数定（08 C2）" % (ns[0], ns[1])
        if variant:
            source += "\n⚠️ 三数为变通法（第三数并入动爻），校本工程（08 C2）只录两数法。"
        r = build(up, low, moving)
        r["source"] = source
    elif a.time:
        if a.lunar_month is None or a.lunar_day is None:
            p.error("时间起卦必须给出 --lunar-month 与 --lunar-day（农历月日，脚本不做农历换算）")
        dt = C.parse_datetime(a.time)
        yb = a.year_branch
        if yb is None:
            from datetime import datetime as _dt
            import _astro
            lc = _astro.term_datetime(dt.year, "立春")
            y = dt.year if dt >= lc else dt.year - 1
            yb = C.ganzhi((y - 4) % 60)[1]
        yb_n = C.ZHI_INDEX[yb] + 1
        hz = C.hour_zhi(dt.hour + dt.minute / 60.0)
        hz_n = C.ZHI_INDEX[hz] + 1
        up, up_n = shu_to_gua(yb_n + a.lunar_month + a.lunar_day)
        low, low_n = shu_to_gua(yb_n + a.lunar_month + a.lunar_day + hz_n)
        moving = dong_yao(yb_n + a.lunar_month + a.lunar_day + hz_n)
        source = ("时间起卦（08 C3）：年支序 %d + 农历月 %d + 农历日 %d"
                  % (yb_n, a.lunar_month, a.lunar_day))
        if hz_n:
            source += "（下卦与动爻另加时支序 %d，%s时）" % (hz_n, hz)
        r = build(up, low, moving)
        r["source"] = source
        r["year_branch"] = yb
        r["hour_zhi"] = hz
    else:
        p.error("请用 --numbers 或 --time 起卦")

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    print("=" * 62)
    print("梅花易数起卦（脚本输出）")
    print("=" * 62)
    print("起卦方式：%s" % r["source"])
    print("上卦 %s（先天数 %d） / 下卦 %s（先天数 %d）"
          % (r["upper"], up_n, r["lower"], low_n))
    print("动爻    ：第 %d 爻 —— 落在%s"
          % (r["moving"], "下卦" if r["moving"] <= 3 else "上卦"))
    print("本卦    ：%s（%s上%s下）" % (r["ben_gua"]["name"], r["upper"], r["lower"]))
    print("互卦    ：%s（过程）" % r["hu_gua"]["name"])
    print("变卦    ：%s（结果）" % r["bian_gua"]["name"])
    print("-" * 62)
    print("体卦 %s（%s）　用卦 %s（%s）"
          % (r["ti"], r["ti_wx"], r["yong"], r["yong_wx"]))
    print("体用判定：%s → %s" % (r["relation"], r["relation_desc"]))
    print("方位    ：体 %s，用 %s（后天八卦，勿与先天数混用）"
          % (r["ti_fangwei"], r["yong_fangwei"]))
    print("-" * 62)
    print("依据：references/08-algorithms.md C 节（先天数、起卦式、体用规则、互变卦）。")
    print("提示：断卦以体用生克 + 卦象为主，不以卦名吉凶；" +
          "判定前务必确认「谁克谁」。")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
