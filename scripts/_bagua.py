# -*- coding: utf-8 -*-
"""
_bagua.py —— 八卦 / 六十四卦 / 纳甲 / 世应（纯标准库）

数据来源（全部引自 references/08-algorithms.md，避免凭记忆抄表）：
  - 八卦爻象、先天八卦数        08 C1
  - 后天八卦方位、先天方位      08 C6
  - 八卦五行                    08 第 0 节
  - 纳甲天干、纳甲地支          08 B2
  - 八宫六十四卦归属表          08 B3
  - 世应规则                    08 B4
  - 体用判定                    08 C4

要点：六十四卦名**不是手抄的**，而是由「八宫表 + 爻变规则」推导生成，
      因此卦名、上下卦、卦宫、世应四者不可能互相对错（见 build_gua_table）。
"""

try:
    from _common import (
        ZHI_WU_XING, GAN_WU_XING, liu_qin, wu_xing_relation, GAN_YANG,
    )
except ImportError:  # 允许作为包导入
    from ._common import (
        ZHI_WU_XING, GAN_WU_XING, liu_qin, wu_xing_relation, GAN_YANG,
    )

# ---------------------------------------------------------------- 三画八卦

# 爻值：1=阳，0=阴；顺序自下而上（初、二、三爻）
TRIGRAM_LINES = {
    "乾": (1, 1, 1),
    "兑": (1, 1, 0),
    "离": (1, 0, 1),
    "震": (1, 0, 0),
    "巽": (0, 1, 1),
    "坎": (0, 1, 0),
    "艮": (0, 0, 1),
    "坤": (0, 0, 0),
}

TRIGRAM_WU_XING = {
    "乾": "金", "兑": "金",
    "震": "木", "巽": "木",
    "坎": "水",
    "离": "火",
    "坤": "土", "艮": "土",
}

# 先天八卦数（起卦用）08 C1 —— 易错：5=巽、6=坎
XIAN_TIAN_SHU = {
    "乾": 1, "兑": 2, "离": 3, "震": 4,
    "巽": 5, "坎": 6, "艮": 7, "坤": 8,
}
SHU_TO_TRIGRAM = {v: k for k, v in XIAN_TIAN_SHU.items()}

# 后天八卦方位（断方位用）08 C6
HOU_TIAN_FANGWEI = {
    "坎": "北", "艮": "东北", "震": "东", "巽": "东南",
    "离": "南", "坤": "西南", "兑": "西", "乾": "西北",
}

# 先天八卦方位（仅供对照，勿与后天混用）08 C6 注
XIAN_TIAN_FANGWEI = {
    "乾": "南", "兑": "东南", "离": "东", "震": "东北",
    "巽": "西南", "坎": "西", "艮": "西北", "坤": "北",
}

# ---------------------------------------------------------------- 纳甲（08 B2）

# 天干：(内卦, 外卦)
NA_JIA_GAN = {
    "乾": ("甲", "壬"),
    "坤": ("乙", "癸"),
    "震": ("庚", "庚"),
    "巽": ("辛", "辛"),
    "坎": ("戊", "戊"),
    "离": ("己", "己"),
    "艮": ("丙", "丙"),
    "兑": ("丁", "丁"),
}

# 地支：自初爻至上爻
NA_JIA_ZHI = {
    "乾": ("子", "寅", "辰", "午", "申", "戌"),
    "震": ("子", "寅", "辰", "午", "申", "戌"),
    "坎": ("寅", "辰", "午", "申", "戌", "子"),
    "艮": ("辰", "午", "申", "戌", "子", "寅"),
    "坤": ("未", "巳", "卯", "丑", "亥", "酉"),
    "巽": ("丑", "亥", "酉", "未", "巳", "卯"),
    "离": ("卯", "丑", "亥", "酉", "未", "巳"),
    "兑": ("巳", "卯", "丑", "亥", "酉", "未"),
}

# ---------------------------------------------------------------- 八宫表（08 B3）

# 顺序与 08-algorithms.md B3 表格行序一致（仅影响遍历顺序，不影响结果）
PALACE_ORDER = ["乾", "震", "坎", "艮", "坤", "巽", "离", "兑"]

PALACE_GUA_NAMES = {
    "乾": ("乾", "姤", "遁", "否", "观", "剥", "晋", "大有"),
    "震": ("震", "豫", "解", "恒", "升", "井", "大过", "随"),
    "坎": ("坎", "节", "屯", "既济", "革", "丰", "明夷", "师"),
    "艮": ("艮", "贲", "大畜", "损", "睽", "履", "中孚", "渐"),
    "坤": ("坤", "复", "临", "泰", "大壮", "夬", "需", "比"),
    "巽": ("巽", "小畜", "家人", "益", "无妄", "噬嗑", "颐", "蛊"),
    "离": ("离", "旅", "鼎", "未济", "蒙", "涣", "讼", "同人"),
    "兑": ("兑", "困", "萃", "咸", "蹇", "谦", "小过", "归妹"),
}

PALACE_WU_XING = {
    "乾": "金", "兑": "金", "离": "火", "震": "木",
    "巽": "木", "坎": "水", "艮": "土", "坤": "土",
}

GEN_NAMES = ("本宫", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂")

# 各代世爻位置（1..6，自下而上）08 B4
SHI_POS_BY_GEN = (6, 1, 2, 3, 4, 5, 4, 3)


def palace_variants(palace: str):
    """生成某宫八重卦的六爻（初..上，1 阳 0 阴）。

    爻变规则（京房八宫）：
      一世：初爻变
      二世：在前基础上二爻变
      …
      五世：在前基础上五爻变
      游魂：五世卦第四爻变回本宫之爻
      归魂：游魂卦内三爻恢复本宫卦之内三爻
    """
    base = list(TRIGRAM_LINES[palace] + TRIGRAM_LINES[palace])
    out = [tuple(base)]
    cur = base[:]
    for i in range(5):
        cur[i] = 1 - cur[i]
        out.append(tuple(cur))
    youhun = list(out[5])
    youhun[3] = 1 - youhun[3]
    out.append(tuple(youhun))
    guihun = list(youhun)
    guihun[0:3] = base[0:3]
    out.append(tuple(guihun))
    return out


def trigram_of(lines3):
    for name, l in TRIGRAM_LINES.items():
        if tuple(lines3) == tuple(l):
            return name
    raise ValueError("非法三爻组合：%r" % (lines3,))


def build_gua_table():
    """由八宫表 + 爻变规则推导 64 卦。返回 {六爻tuple: info dict}。"""
    table = {}
    for palace in PALACE_ORDER:
        for gen, lines in enumerate(palace_variants(palace)):
            name = PALACE_GUA_NAMES[palace][gen]
            lower = trigram_of(lines[0:3])
            upper = trigram_of(lines[3:6])
            shi = SHI_POS_BY_GEN[gen]
            ying = ((shi + 3 - 1) % 6) + 1          # 世应恒隔三位
            if lines in table:
                raise AssertionError("六爻组合重复，八宫表可能有误：%r" % (lines,))
            table[lines] = {
                "name": name,
                "lines": lines,
                "lower": lower,
                "upper": upper,
                "palace": palace,
                "palace_wx": PALACE_WU_XING[palace],
                "gen": GEN_NAMES[gen],
                "gen_index": gen,
                "shi": shi,
                "ying": ying,
            }
    if len(table) != 64:
        raise AssertionError("六十四卦应为 64 项，实得 %d" % len(table))
    return table


GUA64 = build_gua_table()
BY_NAME = {g["name"]: g for g in GUA64.values()}


def gua_of_lines(lines):
    """六爻（初..上）-> 卦信息"""
    return GUA64[tuple(lines)]


def gua_of_name(name: str):
    """支持 64 卦本名（屯/益/否），也支持「水雷屯」「天地否」这类自然象全称。"""
    # 自然象别名 -> 卦名（水=坎、雷=震、火=离、泽=兑、风=巽、山=艮、天=乾、地=坤）
    ALIAS = {"水": "坎", "雷": "震", "火": "离", "泽": "兑",
             "风": "巽", "山": "艮", "天": "乾", "地": "坤"}
    key = name.strip()
    if key in BY_NAME:
        return BY_NAME[key]
    if len(key) == 3:
        up, low = ALIAS.get(key[0], key[0]), ALIAS.get(key[1], key[1])
        if up in TRIGRAM_LINES and low in TRIGRAM_LINES:
            for g in GUA64.values():
                if g["upper"] == up and g["lower"] == low:
                    return g
    raise ValueError("未知卦名：%r（可填 64 卦本名如「屯」「益」，或自然象全称如「水雷屯」）" % name)


def yao_label(pos: int, value: int) -> str:
    """标准爻题：初九 / 六二 / 九五 / 上六 等"""
    n = "九" if value else "六"
    if pos == 0:
        return "初" + n
    if pos == 5:
        return "上" + n
    return n + "二三四五"[pos - 1]        # 六二 / 九五


def zhuang_gua(lines):
    """装卦。

    lines: [(value, moving), ...] 自初爻到上爻，value 1=阳 0=阴，moving 1=动。
    混卦一律**按本卦的上下经卦**纳干纳支（08 B2 混卦规则），不按卦宫。
    返回 (卦信息, 六爻明细列表)。
    """
    base = [v for v, _ in lines]
    info = gua_of_lines(base)
    low, up = info["lower"], info["upper"]
    low_branches, up_branches = NA_JIA_ZHI[low], NA_JIA_ZHI[up]
    rows = []
    for i in range(6):
        trig_name = low if i < 3 else up
        zhi = (low_branches if i < 3 else up_branches)[i]
        gan = (NA_JIA_GAN[low][0] if i < 3 else NA_JIA_GAN[up][1])
        wx = ZHI_WU_XING[zhi]
        rows.append({
            "pos": i + 1,
            "label": yao_label(i, base[i]),
            "value": base[i],
            "moving": bool(lines[i][1]),
            "trigram": trig_name,
            "ganzhi": gan + zhi,
            "wx": wx,
            "liuqin": liu_qin(info["palace_wx"], wx),
            "is_shi": (i + 1) == info["shi"],
            "is_ying": (i + 1) == info["ying"],
        })
    return info, rows


def hu_gua(lines):
    """互卦：二三四爻成下卦，三四五爻成上卦（08 C7）

    02-zhanbu.md 案例校核：晋（离上坤下）→ 二三四爻=艮，三四五爻=坎 → 水山蹇（坎上艮下）。
    """
    base = [v for v, _ in lines]
    lower_hu = tuple(base[1:4])      # 二、三、四爻
    upper_hu = tuple(base[2:5])      # 三、四、五爻
    return GUA64[lower_hu + upper_hu]


def bian_gua(lines):
    """变卦：动爻阴阳互变（08 C7）"""
    return gua_of_lines([(1 - v) if m else v for v, m in lines])


# ---------------------------------------------------------------- 体用（梅花，08 C4）

def ti_yong(upper: str, lower: str, moving_pos: int):
    """动爻位置 1..6 -> (体卦, 用卦)。动爻所在之卦为用卦，另一卦为体卦（08 C4）。"""
    if moving_pos <= 3:     # 动在下卦 → 下卦为用，上卦为体
        return upper, lower
    return lower, upper     # 动在上卦 → 上卦为用，下卦为体


def ti_yong_relation(ti: str, yong: str):
    """体用生克（08 C5）。返回 (关系名, 含义, 体五行, 用五行)"""
    ti_wx, yong_wx = TRIGRAM_WU_XING[ti], TRIGRAM_WU_XING[yong]
    rel = wu_xing_relation(ti_wx, yong_wx)
    name, desc = {
        "同我": ("比和", "体用比和，事易顺"),
        "生我": ("用生体", "事来就我，吉"),
        "我克": ("体克用", "我能控事，需努力"),
        "我生": ("体生用", "我泄气，付出多"),
        "克我": ("用克体", "事压我，费力、阻滞"),
    }[rel]
    return name, desc, ti_wx, yong_wx


if __name__ == "__main__":
    g = gua_of_name("屯")
    print("水雷屯 ->", g["name"], "| 卦宫:", g["palace"], g["palace_wx"],
          "| 世:", g["shi"], "应:", g["ying"], "|", g["gen"])
    info, rows = zhuang_gua([(1, 0), (0, 0), (0, 0), (0, 0), (1, 0), (0, 1)])
    for r in rows:
        print("  %s %s %s(%s) %s %s%s" % (
            r["label"], "阳" if r["value"] else "阴", r["ganzhi"], r["wx"],
            r["liuqin"], ("动" if r["moving"] else "静"),
            ("★世" if r["is_shi"] else "★应" if r["is_ying"] else "")))
    print("互卦:", hu_gua([(1, 0), (0, 0), (0, 0), (0, 0), (1, 0), (0, 1)])["name"])
    print("变卦:", bian_gua([(1, 0), (0, 0), (0, 0), (0, 0), (1, 0), (0, 1)])["name"])
