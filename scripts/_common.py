# -*- coding: utf-8 -*-
"""
_common.py —— 中华术数「确定性换算」共享基础库（纯标准库，零依赖）

定位：
  只负责"可机械推导、无解释歧义"的部分：干支、五行、纳音、藏干、十神、
  六亲、刑冲合害、旬空、六十甲子索引、儒略日。吉凶判断一律交给模型与使用者，
  本库不产出任何断语。

引用源（本文件内所有固定表均来自 zhonghua-shushu/references/08-algorithms.md
第 0 节与 A 节，并经 scripts/_selftest.py 自检）：
  - 天干五行 / 地支五行 / 八卦五行：08 第 0 节
  - 地支藏干：08 A8
  - 十神：08 A7；六亲：08 B5
  - 六十甲子纳音：经外部权威资料交叉核对（名称异写见 scripts/README.md）
"""

from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- 基础序

TIAN_GAN = "甲乙丙丁戊己庚辛壬癸"
DI_ZHI = "子丑寅卯辰巳午未申酉戌亥"
WU_XING = ("木", "火", "土", "金", "水")

GAN_INDEX = {g: i for i, g in enumerate(TIAN_GAN)}   # 甲=0 ... 癸=9
ZHI_INDEX = {z: i for i, z in enumerate(DI_ZHI)}     # 子=0 ... 亥=11

GAN_WU_XING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

ZHI_WU_XING = {
    "亥": "水", "子": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
}

# 阴阳：天干同位序偶数为阳（甲丙戊庚壬），地支子寅辰午申戌为阳
GAN_YANG = set("甲丙戊庚壬")
ZHI_YANG = set("子寅辰午申戌")

SHENG = ("木", "火", "土", "金", "水")   # 相生环


def wu_xing_sheng(a: str, b: str) -> bool:
    """a 生 b"""
    return SHENG[(SHENG.index(a) + 1) % 5] == b


def wu_xing_ke(a: str, b: str) -> bool:
    """a 克 b"""
    return SHENG[(SHENG.index(a) + 2) % 5] == b


def wu_xing_relation(a: str, b: str) -> str:
    """以 a 为「我」，看 b 的关系：同我/我生/我克/克我/生我"""
    if a == b:
        return "同我"
    if wu_xing_sheng(a, b):
        return "我生"
    if wu_xing_ke(a, b):
        return "我克"
    if wu_xing_ke(b, a):
        return "克我"
    return "生我"


def is_yang_gan(g: str) -> bool:
    return g in GAN_YANG


# ---------------------------------------------------------------- 六十甲子

def ganzhi(i: int) -> str:
    """序号 0=甲子 … 59=癸亥"""
    i = int(i) % 60
    return TIAN_GAN[i % 10] + DI_ZHI[i % 12]


def parse_ganzhi(s: str) -> int:
    """「庚午」-> 序号 6；非法组合抛 ValueError（如甲丑）"""
    s = s.strip()
    if len(s) != 2 or s[0] not in GAN_INDEX or s[1] not in ZHI_INDEX:
        raise ValueError("干支须为「天干+地支」两字，收到：%r" % s)
    g, z = GAN_INDEX[s[0]], ZHI_INDEX[s[1]]
    if g % 2 != z % 2:
        raise ValueError("非法干支组合（阴阳不配）：%s" % s)
    for i in range(60):
        if i % 10 == g and i % 12 == z:
            return i
    raise ValueError("非法干支组合：%s" % s)


def jdn(y: int, m: int, d: int) -> int:
    """儒略日数（格里高利历）。仅适用 1582-10-15 之后的公历。"""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return (d + (153 * mm + 2) // 5 + 365 * yy
            + yy // 4 - yy // 100 + yy // 400 - 32045)


# 锚点：2000-01-07 为甲子日（序号 0）。
# 该锚点与 08-algorithms.md A3 一致，并已用三点交叉校验通过（见 _selftest.py）：
#   1949-10-01=甲子 / 2000-01-01=戊午 / 2024-02-10=甲辰
_ANCHOR_JDN = jdn(2000, 1, 7)
_ANCHOR_IDX = 0


def day_ganzhi_index(y: int, m: int, d: int) -> int:
    """任意公历日期的日干支序号"""
    return (_ANCHOR_IDX + (jdn(y, m, d) - _ANCHOR_JDN)) % 60


def day_ganzhi(y=None, m=None, d=None, dt: date = None) -> str:
    if dt is not None:
        y, m, d = dt.year, dt.month, dt.day
    return ganzhi(day_ganzhi_index(y, m, d))


# ---------------------------------------------------------------- 五虎遁 / 五鼠遁

def wuhu_dun(year_gan: str, month_zhi: str) -> str:
    """五虎遁：由年干 + 月支（寅月起）推月干。"""
    g = GAN_INDEX[year_gan]
    z = ZHI_INDEX[month_zhi]
    start = (2 * g + 2) % 10            # 甲己年寅月起丙(2)
    offset = (z - ZHI_INDEX["寅"]) % 12  # 寅=0, 卯=1 ... 丑=11
    return TIAN_GAN[(start + offset) % 10]


def month_ganzhi(year_gan: str, month_zhi: str) -> str:
    return wuhu_dun(year_gan, month_zhi) + month_zhi


def wushu_dun(day_gan: str, hour_zhi: str) -> str:
    """五鼠遁：由日干 + 时支推时干。"""
    g = GAN_INDEX[day_gan]
    z = ZHI_INDEX[hour_zhi]
    start = (2 * g) % 10                # 甲己日子时起甲(0)
    return TIAN_GAN[(start + z) % 10]


def hour_zhi(hour24: float) -> str:
    """小时数（可含小数）-> 时辰地支。23:00-01:00 为子时。"""
    h = hour24 % 24
    idx = int((h + 1) // 2) % 12
    return DI_ZHI[idx]


def next_ganzhi(gz: str, step: int = 1) -> str:
    return ganzhi(parse_ganzhi(gz) + step)


# ---------------------------------------------------------------- 旬空

def xunkong(gz_index_or_str) -> tuple:
    """旬空两支。参数可为序号或「甲辰」类字符串。"""
    i = gz_index_or_str if isinstance(gz_index_or_str, int) else parse_ganzhi(gz_index_or_str)
    i0 = i - (i % 10)                   # 该旬首（甲X）
    b0 = i0 % 12
    return DI_ZHI[(b0 + 10) % 12], DI_ZHI[(b0 + 11) % 12]


# ---------------------------------------------------------------- 地支藏干（08 A8）

CANG_GAN = {
    "子": ("癸",),
    "丑": ("己", "癸", "辛"),
    "寅": ("甲", "丙", "戊"),
    "卯": ("乙",),
    "辰": ("戊", "乙", "癸"),
    "巳": ("丙", "庚", "戊"),
    "午": ("丁", "己"),
    "未": ("己", "丁", "乙"),
    "申": ("庚", "壬", "戊"),
    "酉": ("辛",),
    "戌": ("戊", "辛", "丁"),
    "亥": ("壬", "甲"),
}


# ---------------------------------------------------------------- 十神（08 A7）

def shi_shen(ri_gan: str, target_gan: str) -> str:
    """以日干为「我」，返回 target_gan 的十神。"""
    me_wx, tg_wx = GAN_WU_XING[ri_gan], GAN_WU_XING[target_gan]
    same_yinyang = (ri_gan in GAN_YANG) == (target_gan in GAN_YANG)
    rel = wu_xing_relation(me_wx, tg_wx)
    table = {
        "同我": ("比肩", "劫财"),
        "我生": ("食神", "伤官"),
        "我克": ("偏财", "正财"),
        "克我": ("七杀", "正官"),
        "生我": ("偏印", "正印"),
    }[rel]
    return table[0] if same_yinyang else table[1]


# ---------------------------------------------------------------- 六亲（08 B5）

def liu_qin(gong_wu_xing: str, yao_wu_xing: str) -> str:
    """以卦宫五行为「我」，按爻支五行定六亲。"""
    return {
        "生我": "父母",
        "同我": "兄弟",
        "我生": "子孙",
        "我克": "妻财",
        "克我": "官鬼",
    }[wu_xing_relation(gong_wu_xing, yao_wu_xing)]


# ---------------------------------------------------------------- 地支刑冲合害

LIU_CHONG = [("子", "午"), ("丑", "未"), ("寅", "申"),
             ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]
LIU_HE = [("子", "丑"), ("寅", "亥"), ("卯", "戌"),
          ("辰", "酉"), ("巳", "申"), ("午", "未")]
SAN_HE_JU = [("申", "子", "辰", "水局"), ("亥", "卯", "未", "木局"),
             ("寅", "午", "戌", "火局"), ("巳", "酉", "丑", "金局")]
SAN_XING = [
    ("寅", "巳", "申", "无恩之刑"),
    ("丑", "戌", "未", "恃势之刑"),
    ("子", "卯", None, "无礼之刑"),
    ("辰", None, None, "辰自刑"),
    ("午", None, None, "午自刑"),
    ("酉", None, None, "酉自刑"),
    ("亥", None, None, "亥自刑"),
]
LIU_HAI = [("子", "未"), ("丑", "午"), ("寅", "巳"),
           ("申", "亥"), ("卯", "辰"), ("酉", "戌")]


def _in_sets(zhi_list, pairs):
    out = []
    for pair in pairs:
        need = [x for x in pair[:3] if x]
        if all(x in zhi_list for x in need):
            out.append(pair)
    return out


def zhi_relations(zhi_list) -> dict:
    """输入一串地支（如命局四支+大运+流年），返回成立的所有关系。"""
    zs = list(zhi_list)
    return {
        "六冲": [p for p in LIU_CHONG if p[0] in zs and p[1] in zs],
        "六合": [p for p in LIU_HE if p[0] in zs and p[1] in zs],
        "六害": [p for p in LIU_HAI if p[0] in zs and p[1] in zs],
        "三合": [p for p in SAN_HE_JU if all(x in zs for x in p[:3])],
        "三刑": _in_sets(zs, SAN_XING),
    }


# ---------------------------------------------------------------- 纳音五行
# 每两组干支共一纳音，按六十甲子序 0..29 排列。
# 已与外部权威资料交叉核对；名称存在异写，见 scripts/README.md。
NA_YIN = [
    ("海中金", "金"), ("炉中火", "火"), ("大林木", "木"),
    ("路旁土", "土"), ("剑锋金", "金"), ("山头火", "火"),
    ("涧下水", "水"), ("城头土", "土"), ("白蜡金", "金"),
    ("杨柳木", "木"), ("泉中水", "水"), ("屋上土", "土"),
    ("霹雳火", "火"), ("松柏木", "木"), ("长流水", "水"),
    ("沙中金", "金"), ("山下火", "火"), ("平地木", "木"),
    ("壁上土", "土"), ("金箔金", "金"), ("覆灯火", "火"),
    ("天河水", "水"), ("大驿土", "土"), ("钗钏金", "金"),
    ("桑柘木", "木"), ("大溪水", "水"), ("沙中土", "土"),
    ("天上火", "火"), ("石榴木", "木"), ("大海水", "水"),
]


def na_yin(gz) -> tuple:
    """「庚午」或序号 -> (纳音名, 五行)"""
    i = gz if isinstance(gz, int) else parse_ganzhi(gz)
    return NA_YIN[(i % 60) // 2]


# ---------------------------------------------------------------- 输出辅助

def fmt_pillar(name: str, gz: str, extra: str = "") -> str:
    return "%s：%s%s" % (name, gz, ("　" + extra) if extra else "")


def parse_datetime(s: str) -> datetime:
    """宽松解析：'1990-04-12 10:30' / '1990/4/12 10:30' / '1990-4-12' """
    s = s.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError("无法解析日期时间：%r（示例：1990-04-12 10:30）" % s)


def days_to_age(days: float) -> str:
    """3 天折 1 岁 / 1 天折 4 个月。返回 'X岁Y月' 文本（按已足足数取整，不四舍五入）。"""
    total_months = int(days / 3.0 * 12)      # 向下取整，按「已满」计
    y, m = divmod(total_months, 12)
    if y == 0 and m == 0:
        return "起运极近（<半月）"
    return "%d岁%d月" % (y, m)


if __name__ == "__main__":
    # 快速自查
    print("2000-01-07 =", day_ganzhi(2000, 1, 7), "(应为甲子)")
    print("1949-10-01 =", day_ganzhi(1949, 10, 1), "(应为甲子)")
    print("2000-01-01 =", day_ganzhi(2000, 1, 1), "(应为戊午)")
    print("2024-02-10 =", day_ganzhi(2024, 2, 10), "(应为甲辰)")
    print("庚午年辰月 =", month_ganzhi("庚", "辰"), "(应为庚辰)")
    print("丁未日巳时 =", wushu_dun("丁", "巳") + "巳", "(应为乙巳)")
    print("甲辰旬空 =", xunkong("甲辰"), "(应为寅卯)")
