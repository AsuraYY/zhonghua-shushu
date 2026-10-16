#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
wuge.py —— 姓名五格剖象（纯标准库）

用法（笔画必须由使用者给出，脚本不内置康熙字典笔画库）：
    python wuge.py --surname-strokes 11,12 --given-strokes 8,7
    python wuge.py --surname-strokes 11 --given-strokes 8 --json

五格算法（08 G 节）：
    天格：单姓 = 姓笔画 + 1；复姓 = 各字之和
    人格：姓末字 + 名首字
    地格：单名 = 该字 + 1；复名 = 各字之和
    总格：全部字笔画之和
    外格：流派不一，本脚本用常见的「总格 − 人格」，并同时标注
          「单姓单名假成 1+1=2」之别算結果，供对照。

⚠️ 不输出 81 数理吉凶：那是固定附会，无预测效力（08 G）。
⚠️ 笔画必须以繁体（康熙字典）计；简体计画会得到完全不同的结果。
"""

import argparse
import json
import sys


def calc(surname_strokes, given_strokes):
    surname = list(surname_strokes)
    given = list(given_strokes)
    total_all = sum(surname) + sum(given)
    if len(surname) == 1:
        tian = surname[0] + 1
    else:
        tian = sum(surname)
    ren = surname[-1] + given[0]
    if len(given) == 1:
        di = given[0] + 1
    else:
        di = sum(given)
    zong = total_all
    wai_main = zong - ren
    wai_alt = 1 + 1 if (len(surname) == 1 and len(given) == 1) else None
    return {
        "tian": tian, "ren": ren, "di": di, "zong": zong,
        "wai": wai_main, "wai_alt": wai_alt,
        "note_single_single": (len(surname) == 1 and len(given) == 1),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="姓名五格剖象")
    p.add_argument("--surname-strokes", required=True, help="姓氏笔画，逗号分隔")
    p.add_argument("--given-strokes", required=True, help="名字笔画，逗号分隔")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    def nums(s):
        return [int(x) for x in s.replace("，", ",").split(",") if x.strip()]

    sn = nums(a.surname_strokes)
    gn = nums(a.given_strokes)
    if not sn or not gn:
        p.error("姓氏与名字笔画均不能为空")
    r = calc(sn, gn)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    print("=" * 58)
    print("五格剖象（脚本输出）　姓笔画=%s　名笔画=%s" % (sn, gn))
    print("=" * 58)
    print("  天格 %3d　（%s）" % (r["tian"], "单姓 = 姓+1" if len(sn) == 1 else "复姓各字之和"))
    print("  人格 %3d　（姓末字 + 名首字）" % r["ren"])
    print("  地格 %3d　（%s）" % (r["di"], "单名 = 该字+1" if len(gn) == 1 else "复名各字之和"))
    print("  外格 %3d　（总格 − 人格，常见算法）" % r["wai"])
    if r["wai_alt"] is not None:
        print("        另有外格 %d 之算（单姓单名「假成 1+1」），派别不一。" % r["wai_alt"])
    print("  总格 %3d　（全部字之和）" % r["zong"])
    print("-" * 58)
    print("外格算法各派不一，不宜据此下判断（08 G）。")
    print("本脚本不输出 81 数理吉凶：该表为固定附会，无预测效力。")
    print("五格为近现代产物（日本熊崎健翁创立后传入），仅作参考项。")
    print("笔画请确认按繁体/康熙字典计。")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
