#!/usr/bin/env python3
"""Append a plain-language Chinese explanation banner under each ERC figure/table,
for presenting to a non-expert audience. Keeps the original English figure on top.
Outputs <name>_zh.png/.pdf into docs/research/figures/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import FancyBboxPatch

FIG = Path("docs/research/figures")
CJK = "Arial Unicode MS"          # full Chinese + Latin coverage
ACCENT, BG, INK = "#0B5394", "#EAF2FB", "#16324F"

# plain-language, jargon-free, one sentence each (for a cold audience)
EXPLAIN = {
    "table1_dataset":
        "实验素材：5 份真实的营养与食品标准 PDF，被自动整理成一张含 6 千多个知识点、"
        "2 万多条关系的“知识地图”。",
    "table2_main":
        "传统切片检索几乎找不到该用的关键概念和关系（接近 0），我们的方法能找全近九成、"
        "还能跨更多文档凑齐证据——这是传统方法做不到的能力。",
    "table3_ablation":
        "每加入一个模块，系统“找全证据”的能力就上一个台阶，说明每一项设计都在起正面作用。",
    "table4_quality_latency":
        "加了“知识地图”后回答质量没有下降（甚至略好）；而且对重复出现的相同问题，"
        "借助缓存几乎可以秒答。",
    "table5_query_cache":
        "两层缓存不一样：“检索缓存”复用上次找到的资料、省掉搜索（快约一倍，但答案仍要模型"
        "重写一遍）；“答案缓存”连答案都存好，只对完全相同的问题直接返回（几乎瞬间）。",
    "table6_keyword_cache":
        "“预热”是第一遍把“关键词→候选知识点”写进缓存（这一遍还没省到时间）；“热缓存”是写好"
        "之后再查，原本近 6 秒的知识检索几乎归零（只需 4 毫秒）。",
    "fig_query_cache":
        "注意：这三档都要问题被重复才会命中——最右“答案缓存”要逐字相同的问题才瞬间返回，"
        "这是“重复提问”的最好情况，并不是所有新问题的平均速度。",
    "fig_keyword_cache":
        "缓存填满后，两类最耗时的检索（找概念、找关系）几乎归零；关键优势是不同问题常共用"
        "关键词，因此它能跨问题复用——比“答案缓存”更常命中、更实用。",
}


import re
_PUNCT = "，。、；：）（“”！？·…—"
def zh_wrap(text: str, n: int) -> list[str]:
    # tokenize: keep latin/number runs (e.g. 0.009, 1170×, B5) atomic
    toks = re.findall(r"[0-9A-Za-z][0-9A-Za-z\.\-]*[0-9A-Za-z]|[0-9A-Za-z]|.", text, re.S)
    lines, buf = [], ""
    for t in toks:
        if t in _PUNCT or not buf or len(buf) + len(t) <= n:
            buf += t            # punctuation always sticks to current line
        else:
            lines.append(buf); buf = t
    if buf:
        lines.append(buf)
    return lines


def compose(name: str, text: str):
    src = FIG / f"{name}.png"
    if not src.exists():
        print("skip (missing)", src); return
    img = mpimg.imread(src)
    h_px, w_px = img.shape[0], img.shape[1]
    fig_w = 9.2
    img_h = fig_w * (h_px / w_px)

    chars_per_line = int(fig_w * 3.3)
    lines = zh_wrap(text, chars_per_line)
    line_h = 0.32
    pad = 0.30
    banner_h = pad + len(lines) * line_h + 0.18
    total_h = img_h + banner_h

    fig = plt.figure(figsize=(fig_w, total_h))
    # image on top
    ax_img = fig.add_axes([0, banner_h / total_h, 1, img_h / total_h])
    ax_img.imshow(img); ax_img.axis("off")
    # banner on bottom
    ax_b = fig.add_axes([0, 0, 1, banner_h / total_h]); ax_b.axis("off")
    ax_b.set_xlim(0, 1); ax_b.set_ylim(0, 1)
    ax_b.add_patch(FancyBboxPatch(
        (0.012, 0.10), 0.976, 0.82, boxstyle="round,pad=0.006,rounding_size=0.02",
        linewidth=0, facecolor=BG, mutation_aspect=banner_h * 2.4))
    # accent left bar
    ax_b.add_patch(plt.Rectangle((0.012, 0.10), 0.006, 0.82, color=ACCENT, lw=0))

    y0 = 0.90
    ax_b.text(0.035, y0, "一句话：", fontsize=14.5, fontweight="bold",
              color=ACCENT, va="top", ha="left", fontfamily=CJK)
    indent = 0.035 + 0.094
    for i, ln in enumerate(lines):
        ax_b.text(indent if i == 0 else 0.045, y0 - i * (line_h / banner_h * 0.9),
                  ln, fontsize=13.0, color=INK, va="top", ha="left", fontfamily=CJK)

    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}_zh.{ext}", dpi=200, bbox_inches="tight",
                    pad_inches=0.04, facecolor="white")
    plt.close(fig)
    print(f"wrote {name}_zh.png/.pdf  ({len(lines)} zh line(s))")


for nm, tx in EXPLAIN.items():
    compose(nm, tx)
print("done ->", FIG.resolve())
