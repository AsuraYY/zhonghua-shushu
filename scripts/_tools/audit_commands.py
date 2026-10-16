#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_commands.py —— 第三层校验：文档中写的命令，照抄能不能跑通？

与另外两层的分工：
  _selftest.py        脚本**算得对不对**（数值层）
  audit_vs_doc.py    脚本常量与 08-algorithms.md 表格是否逐格一致（文档层）
  audit_commands.py  文档里出现的命令行，模型照抄后是否真的能执行（命令层）

为什么需要它：模型是照着文档抄命令的。文档里多一个中文注释（如
"--values 1,2,3 自下而上"）就会变成 unrecognized arguments，
这类问题前两层都查不出来。

做法：
  1. 扫描 SKILL.md / references/*.md / scripts/README.md
  2. 正则抽出所有 `python3 scripts/xxx.py ...` 形式的命令
  3. 清洗掉 markdown 语法（反引号、表格转义 \\|、可选段 [...]、括号说明、… 省略号）
  4. 把占位符（YYYY-MM-DD 等）替换成真实值
  5. 逐条 subprocess 实跑，检查退出码

用法：python3 scripts/_tools/audit_commands.py
"""

import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # scripts/_tools
SCRIPTS = os.path.dirname(HERE)                            # scripts
SKILL = os.path.dirname(SCRIPTS)                           # skill 根

# 要扫描的文档
DOC_FILES = [
    os.path.join(SKILL, "SKILL.md"),
    os.path.join(SKILL, "scripts", "README.md"),
]
REF_DIR = os.path.join(SKILL, "references")
if os.path.isdir(REF_DIR):
    for fn in sorted(os.listdir(REF_DIR)):
        if fn.endswith(".md"):
            DOC_FILES.append(os.path.join(REF_DIR, fn))

# 占位符 -> 真实值
PLACEHOLDERS = [
    (r'"YYYY-MM-DD HH:MM"', '"1990-04-12 10:30"'),
    (r'YYYY-MM-DD HH:MM', '"1990-04-12 10:30"'),
    (r'YYYY-MM-DD', '2026-10-16'),
    (r'male\|female', 'male'),
    (r'male|female', 'male'),
]

# 特殊可选段（含中文，无法直接删除，给出具体替换）
OPTIONAL_MAP = {
    "[--lon 经度 | --city 城市]": "--lon 116.41",
}

PASSES = []
FAILS = []
SKIPS = []


def strip_md(s):
    """去掉 markdown 语法噪声。"""
    s = s.replace("`", "")
    s = s.replace("\\|", "|")
    return s


def drop_paren(s):
    """删除中文括号说明段：（）()。"""
    out = []
    depth = 0
    for ch in s:
        if ch in "（(":
            depth += 1
        elif ch in "）)":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def drop_optional_with_cjk(s):
    """剥离文档里表示「可选」的方括号记号 [...]。

    文档写 `[--years 2026,2027]` 是惯例（方括号=可选项），
    但模型照抄时会连方括号一起输入而报错，所以这里一律剥掉。
    个别需要留具体值的（如经度/城市）走 OPTIONAL_MAP。
    """
    for k, v in OPTIONAL_MAP.items():
        s = s.replace(k, v)
    return re.sub(r"\[([^\]]*)\]", "", s)


def drop_ellipsis_args(s):
    """删除 --xxx … 这种省略号参数对。"""
    s = re.sub(r"--[a-z-]+\s+…(\s+--[a-z-]+\s+…)*", "", s)
    s = s.replace("…", "")
    return s


def extract_commands(text):
    """只抽真正的命令行，忽略正文里对脚本名的引用。

    认定为命令的两类：
      a) python/python3 开头的：`python3 scripts/xxx.py ...`
      b) 脚本名后紧跟 -- 参数的：`scripts/xxx.py --values ...`
    裸脚本名（如正文「排盘优先跑 scripts/bazi.py」）不算命令。
    """
    cmds = []
    for m in re.finditer(r"scripts/([a-z_]+\.py)([^\n`]*)", text):
        script, args = m.group(1), m.group(2)
        before = text[max(0, m.start() - 20):m.start()]
        has_py_prefix = re.search(r"python3?\s+$", before) is not None
        has_args = args.lstrip().startswith("--")
        if not (has_py_prefix or has_args):
            continue          # 正文引用，不是命令
        cmds.append((script, args))
    return cmds


def normalize(script, args):
    s = strip_md(args)
    s = drop_paren(s)
    s = s.split("#", 1)[0]              # 去掉行内注释
    s = drop_optional_with_cjk(s)
    s = drop_ellipsis_args(s)
    for pat, rep in PLACEHOLDERS:
        s = s.replace(pat, rep)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def has_stray_cjk(s):
    """命令里是否残留多余的中文。

    允许的情形：中文紧跟在某个 --参数 之后，即它是该参数的值
    （如 `--city 北京`、`--question-type 财`）。
    其余游离中文（如误留在命令里的「自下而上」）一律判为故障。
    """
    for i, tok in enumerate(s.split()):
        if not re.search(r"[\u4e00-\u9fff]", tok):
            continue
        prev = s.split()[i - 1] if i > 0 else ""
        if prev.startswith("--"):        # 是上一个参数的值
            continue
        if re.match(r"^--[a-z-]+=", tok):  # --question-type=财
            continue
        return tok
    return None


def main():
    print("=" * 74)
    print("文档命令可跑性审计（第三层）")
    print("=" * 74)
    print("扫描文档：%d 个\n" % len(DOC_FILES))

    seen = set()
    for path in DOC_FILES:
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, SKILL)
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if "scripts/" not in line:
                    continue
                for script, args in extract_commands(line):
                    norm = normalize(script, args)
                    key = (script, norm)
                    if key in seen:
                        continue
                    seen.add(key)

                    full = os.path.join(SCRIPTS, script)
                    tag = "%s:%d  %s %s" % (rel, lineno, script, norm)

                    # 伪命令（xxx.py 占位）跳过
                    if not os.path.isfile(full):
                        SKIPS.append((tag, "占位脚本，非真实命令"))
                        continue

                    # 中文残留检测
                    stray = has_stray_cjk(norm)
                    if stray:
                        FAILS.append((tag, "命令中残留中文 token「%s」，照抄会报 "
                                           "unrecognized arguments" % stray))
                        continue

                    # 用 shlex 切分，保留 --datetime "1990-04-12 10:30" 里的引号分组
                    try:
                        argv = shlex.split(norm, posix=True)
                    except ValueError:
                        argv = norm.split()
                    cmd = [sys.executable, full] + argv
                    try:
                        p = subprocess.run(cmd, capture_output=True,
                                           timeout=120, cwd=SKILL)
                    except subprocess.TimeoutExpired:
                        FAILS.append((tag, "执行超时"))
                        continue
                    except Exception as e:
                        FAILS.append((tag, "执行异常 %s" % e))
                        continue

                    if p.returncode == 0:
                        PASSES.append(tag)
                    else:
                        err = p.stderr.decode("utf-8", "replace").strip()
                        err = err.splitlines()[-1] if err else "(无 stderr)"
                        FAILS.append((tag, "退出码 %d：%s" % (p.returncode, err)))

    for t, why in SKIPS:
        print("  SKIP | %s\n       └ %s" % (t, why))
    print()
    for t in PASSES:
        print("  ✅ %s" % t)
    print()
    for t, why in FAILS:
        print("  ❌ %s\n       └ %s" % (t, why))

    print()
    print("-" * 74)
    print("  可跑 %d 条 ｜ 失败 %d 条 ｜ 跳过 %d 条（占位命令）"
          % (len(PASSES), len(FAILS), len(SKIPS)))
    if FAILS:
        print("  ⚠️ 文档中存在照抄会报错的命令，请修复后重试。")
        return 1
    print("  🎉 文档中所有真实命令均可照抄执行")
    print("-" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
