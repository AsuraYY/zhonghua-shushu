#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
liuyao.py —— 六爻装卦（纳甲筮法，纯标准库）

用法（三选一给卦）：
    python liuyao.py --values 7,8,7,8,7,8        # 自下而上：6老阴(动) 7少阳 8少阴 9老阳(动)
    python liuyao.py --binary 101010             # 自下而上：1阳 0阴（不动）
    python liuyao.py --name 屯 --moving 6        # 直接给卦名+动爻位置（1=初爻）
    python liuyao.py --name 水雷屯 --moving 6
    python liuyao.py --values 9,8,7,8,7,9 --date 2026-10-16 --question-type 财

可选：
    --date     起卦日期（默认今天）
    --question-type  给出用神建议：财|官/事业|文书/考试|子孙/孩子|出行|疾病|诉讼
    --json     输出 JSON

算法口径全部对齐 references/08-algorithms.md B 节：
    纳甲按**本卦上下经卦**装（非卦宫）、八宫表定卦宫、世应恒隔三位、六亲以卦宫五行为「我」。
"""

import argparse
import json
import sys
from datetime import datetime

import _astro
import _common as C
import _bagua as B

# 六神（六兽）：固定循环序 + 日干起例，一律**自初爻起向上顺排**（《卜筮正宗》一系）
# 歌曰：甲乙起青龙，丙丁起朱雀，戊日起勾陈，己日起螣蛇，庚辛起白虎，壬癸起玄武。
# 核对：实操文献均作「初爻起某神，向上循环」，未见阳顺阴逆；
#       另有「五行归垣」一派按卦宫阴阳逆排，属分支流派，本脚本不采用。
LIU_SHEN = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]
LIU_SHEN_START = {
    "甲": 0, "乙": 0,     # 青龙
    "丙": 1, "丁": 1,     # 朱雀
    "戊": 2,              # 勾陈
    "己": 3,              # 螣蛇
    "庚": 4, "辛": 4,     # 白虎
    "壬": 5, "癸": 5,     # 玄武
}

# 用神建议（依据 references/02-zhanbu.md 第 4 步，勿写入式断言）
YONG_SHEN_HINT = {
    "财": "妻财（问钱财、收入）",
    "官": "官鬼（问功名、职位；注意：也含压力/官非义）",
    "事业": "官鬼为主，兼看父母（单位/文书）；打工求职多参看官鬼，考试多参看父母",
    "文书": "父母（合同、文件、成绩、证书）",
    "考试": "父母（现代考试多取父母为文书成绩，古代功名取官鬼）",
    "子孙": "子孙（孩子、解忧、福德）",
    "孩子": "子孙",
    "出行": "世爻与父母（行程/车船）；忌官鬼克世",
    "疾病": "不看病情本身，请就医；卦中传统以官鬼为病、子孙为医药（仅作民俗参考）",
    "诉讼": "官鬼为对方/官方，世爻为自己，兼看父母（状纸）",
}


def liushen_of_day(day_gan, warn=False):
    """一律自初爻起向上顺排（《卜筮正宗》一系）"""
    start = LIU_SHEN_START[day_gan]
    return [LIU_SHEN[(start + i) % 6] for i in range(6)]


def parse_values(s):
    vals = [int(x) for x in s.replace("，", ",").split(",")]
    if len(vals) != 6:
        raise ValueError("需给 6 个数（自下而上），收到 %d 个" % len(vals))
    out = []
    for v in vals:
        if v == 6:
            out.append((0, True))     # 老阴（阴，动）
        elif v == 7:
            out.append((1, False))    # 少阳
        elif v == 8:
            out.append((0, False))    # 少阴
        elif v == 9:
            out.append((1, True))     # 老阳（阳，动）
        else:
            raise ValueError("爻值只能是 6/7/8/9，收到 %r" % v)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="六爻装卦")
    p.add_argument("--values", help="自下而上 6 个数：6老阴(动) 7少阳 8少阴 9老阳(动)")
    p.add_argument("--binary", help="自下而上 6 位：1阳 0阴（无动爻）")
    p.add_argument("--name", help="卦名，如「屯」「水雷屯」")
    p.add_argument("--moving", default="", help="动爻位置，1-6，逗号分隔（与 --name 配合）")
    p.add_argument("--date", default=None, help="起卦日，默认今天")
    p.add_argument("--question-type", default=None)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    if a.values:
        lines = parse_values(a.values)
    elif a.binary:
        s = a.binary.strip().replace(",", "").replace(" ", "")
        if len(s) != 6 or set(s) - set("01"):
            raise ValueError("--binary 需 6 位 0/1")
        lines = [(int(ch), False) for ch in s]
    elif a.name:
        g = B.gua_of_name(a.name)
        mov = [int(x) for x in a.moving.replace("，", ",").split(",") if x.strip()]
        lines = [(v, (i + 1) in mov) for i, v in enumerate(g["lines"])]
    else:
        p.error("请用 --values / --binary / --name 之一给出卦象")

    dt = C.parse_datetime(a.date) if a.date else datetime.now()
    info, rows = B.zhuang_gua(lines)

    day_gz = C.day_ganzhi(dt=dt.date())
    day_zhi = day_gz[1]
    xk = C.xunkong(day_gz)
    jie_name, _jie_dt, month_zhi = _astro.current_jie(dt)
    ls = liushen_of_day(day_gz[0])

    biangua = B.bian_gua(lines)
    hugua = B.hu_gua(lines)

    for i, r in enumerate(rows):
        r["liushen"] = ls[i]
        r["is_xunkong"] = r["ganzhi"][1] in xk
        r["is_yuepo"] = tuple(sorted((r["ganzhi"][1], month_zhi))) in [
            tuple(sorted(x)) for x in C.LIU_CHONG]

    out = {
        "ben_gua": {k: info[k] for k in ("name", "palace", "palace_wx", "gen", "shi", "ying", "upper", "lower")},
        "bian_gua": {"name": biangua["name"], "upper": biangua["upper"], "lower": biangua["lower"]},
        "hu_gua": {"name": hugua["name"], "upper": hugua["upper"], "lower": hugua["lower"]},
        "date": dt.strftime("%Y-%m-%d"),
        "day_ganzhi": day_gz,
        "month_zhi": month_zhi,
        "month_jie": jie_name,
        "xunkong": xk,
        "moving_positions": [r["pos"] for r in rows if r["moving"]],
        "rows": rows,
    }

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0

    print("=" * 64)
    print("六爻装卦（脚本输出，勿再手工改动数值）")
    print("=" * 64)
    print("起卦日  ：%s  %s日（%s日干支）  → 旬空：%s%s"
          % (dt.strftime("%Y-%m-%d"), day_gz, day_gz, xk[0], xk[1]))
    print("月建    ：%s（%s节之后）" % (month_zhi, jie_name))
    print("本卦    ：%s（%s上%s下）　卦宫：%s宫·%s　卦宫五行：%s"
          % (info["name"], info["upper"], info["lower"], info["palace"],
             info["gen"], info["palace_wx"]))
    print("世应    ：世在%d爻，应在%d爻（恒隔三位）" % (info["shi"], info["ying"]))
    print("变卦    ：%s（%s上%s下）" % (biangua["name"], biangua["upper"], biangua["lower"]))
    print("互卦    ：%s（%s上%s下）" % (hugua["name"], hugua["upper"], hugua["lower"]))
    print("动爻    ：" + ("、".join("%d爻" % x for x in out["moving_positions"]) or "无"))
    print("-" * 64)
    print("%-4s %-6s %-5s %-8s %-4s %-6s %-8s %s"
          % ("爻位", "爻题", "阴阳", "纳干支", "五行", "六亲", "六神", "标记"))
    for r in rows:
        marks = []
        if r["is_shi"]:
            marks.append("★世")
        if r["is_ying"]:
            marks.append("☆应")
        if r["moving"]:
            marks.append("动")
        if r["is_xunkong"]:
            marks.append("空")
        if r["is_yuepo"]:
            marks.append("月破")
        print("%-4s %-6s %-5s %-8s %-4s %-6s %-8s %s"
              % (r["pos"], r["label"], "阳" if r["value"] else "阴",
                 r["ganzhi"], r["wx"], r["liuqin"], r["liushen"], " ".join(marks)))
    print("-" * 64)
    print("六亲以卦宫（%s）为「我」推定；纳干支按本卦上下经卦装（08 B2 混卦规则）。" % info["palace_wx"])
    if a.question_type:
        key = a.question_type.strip()
        hit = YONG_SHEN_HINT.get(key)
        if hit:
            print("用神建议：%s —— 依据 references/02-zhanbu.md「取用神」" % hit)
        else:
            print("用神建议：未知问类「%s」。可选：%s"
                  % (key, " / ".join(YONG_SHEN_HINT.keys())))
    print("六神按日干起例、自初爻向上顺排（《卜筮正宗》一系）；"
          "另有按卦宫阴阳逆排的流派，请以所宗流派为准。")
    print("断卦须依用神旺衰生克，不以卦名吉凶（02-zhanbu 第 5 章警示）。")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
