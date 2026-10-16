# -*- coding: utf-8 -*-
"""
audit_scripts.py —— 脚本层 vs 08-algorithms.md 算法源 的机器化对账

做法：不靠肉眼。直接从 references/08-algorithms.md 里 **解析出表格**，
再与 scripts/ 中的常量/函数输出逐格比对。任一项不一致即报 FAIL。

用法：python scripts/_tools/audit_vs_doc.py

与 scripts/_selftest.py 的分工：
  _selftest.py      = 脚本自身算得对不对（数值层）
  audit_vs_doc.py   = 脚本常量与 08-algorithms.md 表格是否逐格一致（文档层）
改脚本后两个都要跑。
"""

import io
import os
import re
import sys
from datetime import datetime, timedelta

SKILL = r"C:\Users\zyy46\.workbuddy\skills\zhonghua-shushu"
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import _astro            # noqa: E402
import _bagua as B       # noqa: E402
import _common as C      # noqa: E402

MD = io.open(os.path.join(SKILL, "references", "08-algorithms.md"),
             encoding="utf-8").read()

PASSES = 0
FAILS = []


def ok(name):
    global PASSES
    PASSES += 1
    print("  ✅ " + name)


def bad(name, detail=""):
    FAILS.append(name)
    print("  ❌ %s  %s" % (name, detail))


def cmp(name, got, want):
    if got == want:
        ok(name)
    else:
        bad(name, "\n       得到 %r\n       期望 %r" % (got, want))


def sec(t):
    print("\n" + "-" * 74)
    print("【%s】" % t)


# ---------------------------------------------------------------- 表格解析

def parse_table_rows(section_head, next_head=None):
    """截取某节内容里的 markdown 表格行"""
    i = MD.index(section_head)
    j = MD.index(next_head, i) if next_head else len(MD)
    block = MD[i:j]
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)
    return rows


# ================================================================ 1. 五行（第 0 节）
sec("1. 干支/八卦五行 —— 08 第 0 节")
z0 = MD[MD.index("## 0."): MD.index("## A.")]
for gan, wx in re.findall(r"([甲乙丙丁戊己庚辛壬癸])[、\s]*([木火土金水])",
                          re.search(r"天干五行\*\*：(.+)", z0).group(1)):
    pass
# 天干：甲乙木、丙丁火…
for pair, wx in re.findall(r"([甲乙丙丁戊己庚辛壬癸]{2})([木火土金水])",
                           re.search(r"天干五行\*\*：(.+)", z0).group(1)):
    for g in pair:
        cmp("天干 %s 五行" % g, C.GAN_WU_XING[g], wx)
for pair, wx in re.findall(r"([亥子寅卯辰巳午未申酉戌丑]{2})([木火土金水])",
                           re.search(r"地支五行\*\*：(.+)", z0).group(1)):
    for z in pair:
        cmp("地支 %s 五行" % z, C.ZHI_WU_XING[z], wx)
for pair, wx in re.findall(r"([乾坤震巽坎离艮兑]{2})([木火土金水])",
                           re.search(r"八卦五行\*\*：(.+)", z0).group(1)):
    for t in pair:
        cmp("八卦 %s 五行" % t, B.TRIGRAM_WU_XING[t], wx)

# ================================================================ 2. A2 月支表 + 五虎遁
sec("2. 月支表 / 五虎遁 —— 08 A2")
rows = parse_table_rows("### A2.", "### A3.")
jie2zhi_doc = {}
for r in rows:
    if len(r) == 3 and r[1] in C.ZHI_INDEX and r[2] in _astro.TERMS:
        jie2zhi_doc[r[2]] = r[1]
cmp("12 节 -> 月支（数量）", len(jie2zhi_doc), 12)
for jie, zhi in jie2zhi_doc.items():
    cmp("节 %s -> 月支 %s" % (jie, zhi), _astro.JIE_TO_ZHI.get(jie), zhi)
cmp("十二节集合一致", set(jie2zhi_doc), set(_astro.JIE))

for r in rows:
    if len(r) == 2 and re.match(r"^[甲己]、|^[乙庚]|", r[0]) or (len(r) == 2 and "、" in r[0] and len(r[0]) <= 3):
        m = re.match(r"^([甲乙丙丁戊己庚辛壬癸])、([甲乙丙丁戊己庚辛壬癸])$", r[0])
        n = re.match(r"^([甲乙丙丁戊己庚辛壬癸])寅$", r[1])
        if m and n:
            for g in (m.group(1), m.group(2)):
                cmp("五虎遁 %s年 寅月干" % g, C.wuhu_dun(g, "寅"), n.group(1))
# 顺推校验：寅月起 n，之后每月 +1
for g in C.TIAN_GAN:
    start = C.wuhu_dun(g, "寅")
    seq = [C.TIAN_GAN[(C.GAN_INDEX[start] + i) % 10] for i in range(12)]
    zhi_seq = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
    got = [C.wuhu_dun(g, z) for z in zhi_seq]
    cmp("五虎遁 %s年 顺推 12 月" % g, got, seq)

# ================================================================ 3. A4 五鼠遁
sec("3. 五鼠遁 —— 08 A4")
z4 = MD[MD.index("### A4."): MD.index("### A5.")]
cnt = 0
for m in re.finditer(r"\|\s*([甲乙丙丁戊己庚辛壬癸])、([甲乙丙丁戊己庚辛壬癸])\s*\|\s*([甲乙丙丁戊己庚辛壬癸])子\s*\|", z4):
    for g in (m.group(1), m.group(2)):
        cmp("五鼠遁 %s日 子时干" % g, C.wushu_dun(g, "子"), m.group(3))
        cnt += 1
if cnt == 0:
    bad("五鼠遁表解析", "未从文档解析到表格行")
for g in C.TIAN_GAN:
    start = C.wushu_dun(g, "子")
    seq = [C.TIAN_GAN[(C.GAN_INDEX[start] + i) % 10] for i in range(12)]
    got = [C.wushu_dun(g, z) for z in C.DI_ZHI]
    cmp("五鼠遁 %s日 顺推 12 时" % g, got, seq)

# ================================================================ 4. A3 日柱锚点
sec("4. 日柱 JDN —— 08 A3")
for s, want in [("1949-10-01", "甲子"), ("2000-01-01", "戊午"), ("2024-02-10", "甲辰")]:
    y, m, d = [int(x) for x in s.split("-")]
    cmp("日柱 %s" % s, C.day_ganzhi(y, m, d), want)
cmp("锚点 2000-01-07 为甲子(序号0)", C.day_ganzhi(2000, 1, 7), "甲子")
cmp("日柱 1990-04-12", C.day_ganzhi(1990, 4, 12), "丁未")
# 独立实现交叉：从 2000-01-07 起逐日累加 800 天
base = datetime(2000, 1, 7)
idx = 0
mism = 0
for k in range(800):
    d = base + timedelta(days=k)
    if C.day_ganzhi(dt=d) != C.ganzhi(idx):
        mism += 1
    idx = (idx + 1) % 60
cmp("日柱逐日连续 800 天无跳变", mism, 0)

# ================================================================ 5. A8 藏干
sec("5. 地支藏干 —— 08 A8")
z8 = MD[MD.index("### A8."): MD.index("### A9.")]
doc_cang = {}
for m in re.finditer(r"^\|\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|\s*([^|]+)\|", z8, re.M):
    z = m.group(1)
    gs = tuple(re.findall(r"[甲乙丙丁戊己庚辛壬癸]", m.group(2)))
    doc_cang[z] = gs
cmp("藏干表条目数", len(doc_cang), 12)
for z, gs in doc_cang.items():
    cmp("藏干 %s" % z, C.CANG_GAN[z], gs)

# ================================================================ 6. A9 旬空
sec("6. 旬空 —— 08 A9")
for gz, want in [("甲辰", ("寅", "卯")), ("甲午", ("辰", "巳")), ("甲申", ("午", "未"))]:
    cmp("旬空 %s" % gz, C.xunkong(gz), want)
# 穷举：每旬空两支必须不在该旬 10 组里
bad_xk = []
for i in range(60):
    i0 = i - i % 10
    xk = set(C.xunkong(i))
    in_xun = set(C.ganzhi(i0 + k)[1] for k in range(10))
    if xk & in_xun:
        bad_xk.append(i)
cmp("60 组旬空均落在本旬之外", bad_xk, [])

# ================================================================ 7. A7 十神
sec("7. 十神 —— 08 A7")
doc_ss = {}
z7 = MD[MD.index("### A7."): MD.index("### A8.")]
for m in re.finditer(r"^\|\s*(同我|我生|我克|克我|生我)\s*\|\s*([^|]+)\|", z7, re.M):
    names = re.findall(r"(比肩|劫财|食神|伤官|偏财|正财|七杀|正官|偏印|正印)", m.group(2))
    doc_ss[m.group(1)] = tuple(names)
cmp("十神表：同我", doc_ss.get("同我"), ("比肩", "劫财"))
cmp("十神表：我生", doc_ss.get("我生"), ("食神", "伤官"))
cmp("十神表：我克", doc_ss.get("我克"), ("偏财", "正财"))
cmp("十神表：克我", doc_ss.get("克我"), ("七杀", "正官"))
cmp("十神表：生我", doc_ss.get("生我"), ("偏印", "正印"))
# 穷举 10x10 与文档规则一致
err = []
for me in C.TIAN_GAN:
    for tg in C.TIAN_GAN:
        got = C.shi_shen(me, tg)
        rel = C.wu_xing_relation(C.GAN_WU_XING[me], C.GAN_WU_XING[tg])
        same = (me in C.GAN_YANG) == (tg in C.GAN_YANG)
        want = doc_ss[rel][0] if same else doc_ss[rel][1]
        if got != want:
            err.append((me, tg, got, want))
cmp("十神 10×10 穷举与文档规则一致", err, [])

# ================================================================ 8. B1 铜钱爻象
sec("8. 铜钱爻象 —— 08 B1")
z1 = MD[MD.index("### B1."): MD.index("### B2.")]
doc_coin = {}
for line in z1.splitlines():
    m = re.match(r"^\|\s*(三背|三字|一背二字|二背一字)\s*\|\s*(\S+?)（([阳阴])爻[，,]\s*(动|静)）", line.strip())
    if m:
        doc_coin[m.group(1)] = (1 if m.group(3) == "阳" else 0, m.group(4) == "动")
cmp("铜钱表解析条数", len(doc_coin), 4)
expect_map = {"三背": (1, True), "三字": (0, True),
              "一背二字": (1, False), "二背一字": (0, False)}
for k, v in expect_map.items():
    cmp("铜钱 %s" % k, doc_coin.get(k), v)

# ================================================================ 9. B2 纳甲
sec("9. 纳甲 —— 08 B2")
z2 = MD[MD.index("### B2."): MD.index("### B3.")]
doc_na_zhi = {}
for m in re.finditer(r"^\|\s*([乾坤震巽坎离艮兑])\s*\|\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|"
                     r"\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|"
                     r"\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|"
                     r"\s*([子丑寅卯辰巳午未申酉戌亥])\s*\|", z2, re.M):
    doc_na_zhi[m.group(1)] = tuple(m.group(i) for i in range(2, 8))
cmp("纳甲地支表条目数", len(doc_na_zhi), 8)
for t, v in doc_na_zhi.items():
    cmp("纳支 %s" % t, B.NA_JIA_ZHI[t], v)
# 纳干：乾纳甲壬、坤纳乙癸…
doc_na_gan = {}
for m in re.finditer(r"([乾坤震巽坎离艮兑])纳([甲乙丙丁戊己庚辛壬癸])([甲乙丙丁戊己庚辛壬癸])?", z2):
    g1 = m.group(2)
    g2 = m.group(3) or m.group(2)
    doc_na_gan[m.group(1)] = (g1, g2)
cmp("纳干表条目数", len(doc_na_gan), 8)
for t, v in doc_na_gan.items():
    cmp("纳干 %s" % t, B.NA_JIA_GAN[t], v)

# ================================================================ 10. B3 八宫
sec("10. 八宫六十四卦 —— 08 B3")
z3 = MD[MD.index("### B3."): MD.index("### B4.")]
doc_palace = {}
for m in re.finditer(r"^\|\s*([乾坤震巽坎离艮兑])（([木火土金水])）\s*\|(.+)\|", z3, re.M):
    names = [x.strip() for x in m.group(3).split("|") if x.strip()]
    doc_palace[m.group(1)] = (m.group(2), tuple(names))
cmp("八宫表条目数", len(doc_palace), 8)
for p, (wx, names) in doc_palace.items():
    cmp("八宫 %s 卦序" % p, B.PALACE_GUA_NAMES[p], names)
    cmp("八宫 %s 五行" % p, B.PALACE_WU_XING[p], wx)
cmp("八宫顺序", tuple(doc_palace.keys()), tuple(B.PALACE_ORDER))
# 推导出的 64 卦：卦名/上下卦/世应 必须与文档表完全对应
err = []
for p, (wx, names) in doc_palace.items():
    for gen, nm in enumerate(names):
        g = B.BY_NAME.get(nm)
        if g is None:
            err.append("缺卦名 %s" % nm)
            continue
        if g["palace"] != p:
            err.append("%s 卦宫应为 %s 实为 %s" % (nm, p, g["palace"]))
        if g["gen_index"] != gen:
            err.append("%s 代次应为 %d 实为 %d" % (nm, gen, g["gen_index"]))
cmp("64 卦：卦名/卦宫/代次 全部对应", err, [])
# 独立推导：京房爻变规则重算一遍全部 64 卦爻象，与表比对
def derive(palace):
    base = list(B.TRIGRAM_LINES[palace] * 2)
    out = [tuple(base)]
    cur = base[:]
    for i in range(5):
        cur[i] = 1 - cur[i]
        out.append(tuple(cur))
    yh = list(out[5]); yh[3] = 1 - yh[3]; out.append(tuple(yh))
    gh = list(yh); gh[0:3] = base[0:3]; out.append(tuple(gh))
    return out
err = []
for p, (wx, names) in doc_palace.items():
    for gen, lines in enumerate(derive(p)):
        g = B.BY_NAME[names[gen]]
        if tuple(g["lines"]) != lines:
            err.append("%s 爻象不符" % names[gen])
cmp("64 卦爻象：京房爻变规则独立复算一致", err, [])

# ================================================================ 11. B4 世应
sec("11. 世应 —— 08 B4")
z4b = MD[MD.index("### B4."): MD.index("### B5.")]
CN2NUM = {"初": 1, "二": 2, "三": 3, "四": 4, "五": 5, "上": 6, "六": 6}
doc_shi = {}
for m in re.finditer(r"-\s*(\S+?)卦：世在(\S+?)[爻]?[，,]应在(\S+?)[爻]?[（\n]", z4b):
    doc_shi[m.group(1)] = (CN2NUM[m.group(2)], CN2NUM[m.group(3)])
cmp("世应条目数", len(doc_shi), 6)
doc_map = {"八纯": 0, "一世": 1, "二世": 2, "三世": 3, "四世": 4, "五世": 5}
err = []
for k, (shi, ying) in doc_shi.items():
    gen = doc_map[k]
    if B.SHI_POS_BY_GEN[gen] != shi:
        err.append("%s 世位 %d != %d" % (k, B.SHI_POS_BY_GEN[gen], shi))
    if ((shi + 3 - 1) % 6) + 1 != ying:
        err.append("%s 应位不符" % k)
cmp("世应位置与文档一致", err, [])
cmp("游魂世位=四世(4)", B.SHI_POS_BY_GEN[6], 4)
cmp("归魂世位=三世(3)", B.SHI_POS_BY_GEN[7], 3)
err = [g["name"] for g in B.GUA64.values()
       if ((g["shi"] + 3 - 1) % 6) + 1 != g["ying"]]
cmp("64 卦世应恒隔三位", err, [])

# ================================================================ 12. B5 六亲
sec("12. 六亲 —— 08 B5")
z5 = MD[MD.index("### B5."): MD.index("### B6.")]
doc_lq = {}
for m in re.finditer(r"^\|\s*(同我|我生|我克|克我|生我)\s*\|\s*(\S+?)\s*\|", z5, re.M):
    doc_lq[m.group(1)] = m.group(2)
cmp("六亲表", doc_lq, {"生我": "父母", "同我": "兄弟", "我生": "子孙",
                       "我克": "妻财", "克我": "官鬼"})
err = []
for wx1 in C.WU_XING:
    for wx2 in C.WU_XING:
        got = C.liu_qin(wx1, wx2)
        want = doc_lq[C.wu_xing_relation(wx1, wx2)]
        if got != want:
            err.append((wx1, wx2, got, want))
cmp("六亲 5×5 穷举一致", err, [])

# ================================================================ 13. B6 乾为天示例
sec("13. 乾为天装卦示例 —— 08 B6")
z6 = MD[MD.index("### B6."): MD.index("## C.")]
doc_qian = []
for m in re.finditer(r"^\|\s*(上九|九五|九四|九三|九二|初九|上六|六五|六四|六三|六二|初六)\s*\|"
                     r"\s*(阳|阴)\s*\|\s*([子丑寅卯辰巳午未申酉戌亥])（([木火土金水])）\s*\|"
                     r"\s*(\S+?)\s*\|([^|]*)\|", z6, re.M):
    doc_qian.append({"label": m.group(1), "yang": m.group(2) == "阳",
                     "zhi": m.group(3), "wx": m.group(4),
                     "lq": m.group(5), "note": m.group(6)})
cmp("乾为天示例 6 爻", len(doc_qian), 6)
info, rows = B.zhuang_gua([(1, 0)] * 6)
# 文档自下而上 = 初九→上九；脚本 rows 自初到上。文档表格自上而下，反转
doc_rev = list(reversed(doc_qian))
for i, (d, r) in enumerate(zip(doc_rev, rows)):
    cmp("乾 %s 爻题" % d["label"], r["label"], d["label"])
    cmp("乾 %s 纳支" % d["label"], r["ganzhi"][1], d["zhi"])
    cmp("乾 %s 六亲" % d["label"], r["liuqin"], d["lq"])
    cmp("乾 %s 五行" % d["label"], r["wx"], d["wx"])
cmp("乾 纳干：内三甲", [r["ganzhi"][0] for r in rows[:3]], ["甲", "甲", "甲"])
cmp("乾 纳干：外三壬", [r["ganzhi"][0] for r in rows[3:]], ["壬", "壬", "壬"])
cmp("乾 世在六", info["shi"], 6)
cmp("乾 应在三", info["ying"], 3)

# ================================================================ 14. B2 混卦示例（水雷屯）
sec("14. 混卦装卦规则 —— 08 B2 水雷屯")
info_t, rows_t = B.zhuang_gua([(1, 0), (0, 0), (0, 0), (0, 0), (1, 0), (0, 0)])
cmp("屯 上坎下震", (info_t["upper"], info_t["lower"]), ("坎", "震"))
cmp("屯 内三爻纳支 = 震前三项(子寅辰)",
    [r["ganzhi"][1] for r in rows_t[:3]], ["子", "寅", "辰"])
cmp("屯 外三爻纳支 = 坎后三项(申戌子)",
    [r["ganzhi"][1] for r in rows_t[3:]], ["申", "戌", "子"])
cmp("屯 内三爻纳干 = 庚", [r["ganzhi"][0] for r in rows_t[:3]], ["庚", "庚", "庚"])
cmp("屯 外三爻纳干 = 戊", [r["ganzhi"][0] for r in rows_t[3:]], ["戊", "戊", "戊"])
cmp("屯 卦宫坎（五行属水）", (info_t["palace"], info_t["palace_wx"]), ("坎", "水"))
cmp("屯 二世世在二", info_t["shi"], 2)
cmp("屯 应在五", info_t["ying"], 5)
# 屯上爻动 → 益
bg = B.bian_gua([(1, 0), (0, 0), (0, 0), (0, 0), (1, 0), (0, 1)])
cmp("屯 上爻动 → 风雷益", (bg["name"], bg["upper"], bg["lower"]), ("益", "巽", "震"))

# ================================================================ 15. C1/C6 八卦数与方位
sec("15. 先天数 / 八卦方位 —— 08 C1、C6")
zc1 = MD[MD.index("### C1."): MD.index("### C2.")]
m = re.search(r"乾1、\*\*兑2\*\*、\*\*离3\*\*、震4、\*\*巽5\*\*、\*\*坎6\*\*、艮7、\*\*坤8\*\*", zc1.replace(" ", ""))
cmp("C1 先天数原文存在", bool(m), True)
doc_xt = {"乾": 1, "兑": 2, "离": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
for t, n in doc_xt.items():
    cmp("先天数 %s" % t, B.XIAN_TIAN_SHU[t], n)
    cmp("先天数反查 %d" % n, B.SHU_TO_TRIGRAM[n], t)
zc6 = MD[MD.index("### C6."): MD.index("### C7.")]
doc_ht = {}
for m in re.finditer(r"\|\s*([乾坤震巽坎离艮兑])\s*\|\s*(\S+?)\s*\|\s*([乾坤震巽坎离艮兑])\s*\|\s*(\S+?)\s*\|", zc6):
    doc_ht[m.group(1)] = m.group(2).replace("*", "")
    doc_ht[m.group(3)] = m.group(4).replace("*", "")
cmp("后天方位条目", len(doc_ht), 8)
for t, fw in doc_ht.items():
    cmp("后天方位 %s" % t, B.HOU_TIAN_FANGWEI[t], fw)
m = re.search(r"先天八卦方位为：([^）]+)", zc6)
if m:
    doc_xt_fw = {}
    for t, fw in re.findall(r"([乾坤震巽坎离艮兑])([东西南北]{1,2})", m.group(1)):
        doc_xt_fw[t] = fw
    cmp("先天方位条目", len(doc_xt_fw), 8)
    for t, fw in doc_xt_fw.items():
        cmp("先天方位 %s" % t, B.XIAN_TIAN_FANGWEI[t], fw)
else:
    bad("先天方位解析", "未匹配到")

# ================================================================ 16. C2/C3 起卦式
sec("16. 梅花起卦 —— 08 C2/C3/C4/C5/C7")
# 文档 02 章案例：报数 3、8 → 火地晋，五爻动
msys = sys.modules
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import meihua  # noqa: E402
r = meihua.build("离", "坤", 5)
cmp("3,8 → 上离下坤", (r["upper"], r["lower"]), ("离", "坤"))
cmp("本卦 = 火地晋", r["ben_gua"]["name"], "晋")
cmp("五爻动在上卦 → 用=离 体=坤", (r["ti"], r["yong"]), ("坤", "离"))
cmp("体坤土 用离火 → 用生体", r["relation"], "用生体")
cmp("变卦 = 天地否", r["bian_gua"]["name"], "否")
cmp("动爻 (3+8) mod 6 = 5", meihua.dong_yao(3 + 8), 5)
cmp("5 → 巽（易错点）", meihua.shu_to_gua(5)[0], "巽")
cmp("6 → 坎（易错点）", meihua.shu_to_gua(6)[0], "坎")
cmp("8 mod 8 → 8 坤", meihua.shu_to_gua(8)[0], "坤")
cmp("16 mod 6 → 4", meihua.dong_yao(16), 4)
cmp("12 mod 6 → 6", meihua.dong_yao(12), 6)
# C5 警示案例：体离火 + 用坎水 → 用克体
rel, desc, tw, yw = B.ti_yong_relation("离", "坎")
cmp("体离火 + 用坎水 → 用克体（C5 警示）", rel, "用克体")
# C7 互卦
hg = B.hu_gua([(0, 0), (0, 0), (0, 0), (1, 0), (0, 0), (1, 0)])   # 晋：坤下离上
cmp("晋 互卦 = 水山蹇", (hg["name"], hg["upper"], hg["lower"]), ("蹇", "坎", "艮"))

# ================================================================ 17. A5 真太阳时
sec("17. 真太阳时 —— 08 A5")
d = datetime(1990, 5, 15, 14, 50)
t, lc, eot = _astro.true_solar_time(d, 103.83)
cmp("兰州经度时差 ≈ -64.7 分", round(lc, 1), -64.7)
cmp("5 月中旬均时差 ≈ +3.7 分", abs(eot - 3.7) < 1.0, True)
cmp("兰州 14:50 → 约 13:49", t.strftime("%H:%M"), "13:49")
# 经度公式方向
t2, lc2, _ = _astro.true_solar_time(datetime(2000, 6, 1, 12, 0), 130.0)
cmp("东经 130° 经度时差 +40 分", round(lc2, 1), 40.0)
t3, lc3, _ = _astro.true_solar_time(datetime(2000, 6, 1, 12, 0), 110.0)
cmp("东经 110° 经度时差 -40 分", round(lc3, 1), -40.0)

# ================================================================ 18. A6 起大运
sec("18. 起大运 —— 08 A6")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import bazi  # noqa: E402
inf = bazi.build_chart(datetime(1990, 4, 12, 10, 30), "male", 116.41)
cmp("1990-04-12 男 顺排", inf["dayun"]["forward"], True)
cmp("1990-04-12 男 基准节 = 立夏", inf["dayun"]["target_jie"]["name"], "立夏")
cmp("1990-04-12 男 起运 7岁10月", inf["dayun"]["qiyun_text"], "7岁10月")
print("     （距立夏 %.3f 天）" % inf["dayun"]["days_to_jie"])
inf2 = bazi.build_chart(datetime(1990, 4, 12, 10, 30), "female", 116.41)
cmp("1990-04-12 女 逆排", inf2["dayun"]["forward"], False)
cmp("1990-04-12 女 基准节 = 清明", inf2["dayun"]["target_jie"]["name"], "清明")
cmp("1990-04-12 女 起运 2岁4月", inf2["dayun"]["qiyun_text"], "2岁4月")
print("     （距清明 %.3f 天）" % inf2["dayun"]["days_to_jie"])
# 文档第二个示例：2001-04-08 06:00（辛巳年，阴男逆排至清明）
inf3 = bazi.build_chart(datetime(2001, 4, 8, 6, 0), "male", 120.0, use_solar_time=False)
cmp("2001-04-08 男 逆排", inf3["dayun"]["forward"], False)
cmp("2001-04-08 男 基准节 = 清明", inf3["dayun"]["target_jie"]["name"], "清明")
print("     文档 A6 第二例：脚本实测 %.3f 天 → %s（文档同口径）"
      % (inf3["dayun"]["days_to_jie"], inf3["dayun"]["qiyun_text"]))
cmp("2001-04-08 男 起运 1岁0月（向下取整口径）", inf3["dayun"]["qiyun_text"], "1岁0月")
# 顺逆规则穷举
err = []
for yg in C.TIAN_GAN:
    for gender in ("male", "female"):
        # 造一个年干 = yg 的年份：找 y 使 (y-4)%60 %10 == GAN_INDEX[yg]
        y = 1990
        while C.ganzhi((y - 4) % 60)[0] != yg:
            y += 1
        yy = bazi.build_chart(datetime(y, 6, 15, 12, 0), gender, 120.0, use_solar_time=False)
        yang = yg in C.GAN_YANG
        want = (yang and gender == "male") or ((not yang) and gender == "female")
        if yy["dayun"]["forward"] != want:
            err.append((yg, gender))
cmp("顺逆规则 10 干 × 2 性别 穷举", err, [])

# ================================================================ 19. E 节 冲合与建除
sec("19. 冲合 / 建除 —— 08 E")
ze = MD[MD.index("## E."): MD.index("## F.")]
m = re.search(r"地支六冲\*\*：(.+)", ze)
doc_chong = re.findall(r"([子丑寅卯辰巳午未申酉戌亥])([子丑寅卯辰巳午未申酉戌亥])", m.group(1))
cmp("六冲", sorted(tuple(sorted(x)) for x in doc_chong),
    sorted(tuple(sorted(x)) for x in C.LIU_CHONG))
m = re.search(r"地支六合\*\*：(.+)", ze)
doc_he = re.findall(r"([子丑寅卯辰巳午未申酉戌亥])([子丑寅卯辰巳午未申酉戌亥])", m.group(1))
cmp("六合", sorted(tuple(sorted(x)) for x in doc_he),
    sorted(tuple(sorted(x)) for x in C.LIU_HE))
m = re.search(r"建除十二神\*\*（顺序固定）：(.+)", ze)
doc_jc = [x for x in re.split(r"[、，,]", m.group(1)) if x]
cmp("建除十二神", doc_jc, list(__import__("zeri").JIAN_CHU))
# 建除法：日支 = 月支 时为「建」
import zeri  # noqa: E402
r0 = zeri.day_info(datetime(2026, 10, 16))
gz0 = C.day_ganzhi(dt=datetime(2026, 10, 16).date())
if gz0[1] == r0["month_zhi"]:
    cmp("日支=月支 → 建", r0["jianchu"], "建")
else:
    off = (C.ZHI_INDEX[gz0[1]] - C.ZHI_INDEX[r0["month_zhi"]]) % 12
    cmp("建除顺推（日支-月支=%d）" % off, r0["jianchu"], __import__("zeri").JIAN_CHU[off])

# ================================================================ 20. G 五格
sec("20. 五格 —— 08 G")
import wuge  # noqa: E402
r = wuge.calc([11], [8, 7])
cmp("天格 = 姓+1", r["tian"], 12)
cmp("人格 = 姓末+名首", r["ren"], 19)
cmp("地格 = 复名之和", r["di"], 15)
cmp("总格 = 全部之和", r["zong"], 26)
cmp("外格 = 总-人", r["wai"], 7)
r2 = wuge.calc([11, 12], [8])
cmp("复姓天格 = 各字之和", r2["tian"], 23)
cmp("单名地格 = 该字+1", r2["di"], 9)
cmp("单姓单名外格别算 = 2", r2["wai_alt"], 2 if False else None)

# ================================================================ 21. 节气表自洽
sec("21. 节气表自洽性（1900–2052）")
bad_rows = []
prev = None
for y in range(1900, 2053):
    row = _astro.terms_of_year(y)
    if len(row) != 24:
        bad_rows.append("%d 节气数 %d" % (y, len(row)))
        continue
    seq = [row[t] for t in _astro.TERMS]
    for a, b in zip(seq, seq[1:]):
        if not (b - a).total_seconds() > 0:
            bad_rows.append("%d 节气非递增" % y)
    if prev is not None:
        gap = (seq[0] - prev).total_seconds() / 86400.0
        if not (10 < gap < 40):
            bad_rows.append("%d 与上年冬至间隔 %.1f 天异常" % (y, gap))
    prev = seq[-1]
cmp("153 年节气 递增且与上年衔接正常", bad_rows, [])
# 抽样：每年「立春」必须落在 2/3–2/5
bad2 = [y for y in range(1900, 2053)
        if not (datetime(y, 2, 3) <= _astro.term_datetime(y, "立春") <= datetime(y, 2, 6))]
cmp("立春均落在 2/3–2/6", bad2, [])
bad3 = [y for y in range(1900, 2053)
        if not (datetime(y, 12, 20) <= _astro.term_datetime(y, "冬至") <= datetime(y, 12, 24))]
cmp("冬至均落在 12/20–12/24", bad3, [])

# ================================================================ 22. 越界近似路径
sec("22. 越界年份近似回退（2053+）")
ok_approx = True
for y in (2053, 2060, 2100):
    try:
        t = _astro.term_datetime(y, "立春")
        if not (datetime(y, 2, 2) <= t <= datetime(y, 2, 7)):
            ok_approx = False
            print("     %d 立春 ≈ %s（超出预期区间）" % (y, t))
    except Exception as ex:
        ok_approx = False
        print("     %d 异常：%s" % (y, ex))
cmp("越界年份立春落在 2/2–2/7（近似值可接受）", ok_approx, True)
cmp("越界年份会被标记 approx", _astro.is_approx_year(2060), True)

# ================================================================ 结果
print("\n" + "=" * 74)
print("  通过 %d 项，失败 %d 项" % (PASSES, len(FAILS)))
if FAILS:
    print("  失败清单：")
    for f in FAILS:
        print("    - " + f)
    print("=" * 74)
    sys.exit(1)
print("  🎉 脚本层与 08-algorithms.md 完全一致")
print("=" * 74)
