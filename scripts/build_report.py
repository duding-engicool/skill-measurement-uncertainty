#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测量不确定度（MU）评定报告生成器 —— 按 GUM 法（A 类 / B 类分量合成）
读入结构化结果 JSON，生成 MD 文档 + 网页版 HTML（双版）。主色 #C8102E。

用法：
  python build_report.py --input result.json --md-out report.md --html-out report.html
  python build_report.py --demo            # 使用内置小样本

输入 JSON 结构：
{
  "title":"测量不确定度评定报告",
  "measurand":"某轴径",
  "unit":"mm",
  "nominal":"10.000",
  "procedure":"三坐标测量机（待企业补充）",
  "A": {"measurements":[10.012,10.015,10.013,10.014,10.011,10.016]},
  "B":[
    {"name":"仪器分辨率","a":0.0005,"dist":"rect","c":1},
    {"name":"校准不确定度","a":0.002,"dist":"norm","k":2,"c":1},
    {"name":"温度影响","a":0.0015,"dist":"rect","c":1}
  ],
  "k":2,
  "conclusion":"（可选）"
}
说明：
 - A 类：u_A = s/√n（s 为样本标准差，n 为观测次数）
 - B 类：u = c × a / 除数；rect 除数 √3，tri 除数 √6，norm 除数 k
 - 合成：u_c = √(u_A² + Σ u_B²)
 - 扩展：U = k × u_c（k 默认 2，约 95%）
"""
import argparse
import json
import sys
import html
import math
from datetime import datetime

PRIMARY = "#C8102E"


def esc(s):
    return html.escape(str(s), quote=True)


def load_result(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def divisor_for(dist, k):
    d = (dist or "rect").lower()
    if d in ("rect", "uniform", "矩形", "均匀"):
        return math.sqrt(3), "矩形(均匀) a/√3"
    if d in ("tri", "triangle", "三角"):
        return math.sqrt(6), "三角 a/√6"
    if d in ("norm", "normal", "正态"):
        kk = k if k else 2
        return float(kk), f"正态 a/{kk}"
    # 默认按矩形
    return math.sqrt(3), "矩形(均匀) a/√3（默认）"


def evaluate(r):
    """返回计算细节字典。"""
    res = {}
    A = r.get("A", {}) or {}
    meas = A.get("measurements", []) or []
    if meas and len(meas) >= 2:
        n = len(meas)
        mean = sum(meas) / n
        var = sum((x - mean) ** 2 for x in meas) / (n - 1)
        s = math.sqrt(var)
        uA = s / math.sqrt(n)
        res["A"] = {"n": n, "mean": mean, "s": s, "uA": uA, "has": True}
    else:
        res["A"] = {"n": len(meas), "mean": None, "s": None, "uA": 0.0, "has": False}

    B = []
    k = r.get("k", 2) or 2
    for b in r.get("B", []) or []:
        a = b.get("a", 0) or 0
        c = b.get("c", 1) if b.get("c") is not None else 1
        div, formula = divisor_for(b.get("dist"), b.get("k", k))
        u = (c * a / div) if div else 0.0
        B.append({"name": b.get("name", "待企业补充"), "a": a, "dist": b.get("dist", "rect"),
                  "c": c, "div": div, "formula": formula, "u": u})
    res["B"] = B

    uA = res["A"]["uA"]
    u_c = math.sqrt(uA ** 2 + sum(x["u"] ** 2 for x in B))
    U = k * u_c
    res["k"] = k
    res["u_c"] = u_c
    res["U"] = U
    res["mean"] = res["A"]["mean"]
    if res["mean"] is not None and res["mean"] != 0:
        res["rel"] = U / abs(res["mean"])
    else:
        res["rel"] = None
    return res


def build_md(r):
    e = evaluate(r)
    L = []
    L.append(f"# {r.get('title','测量不确定度评定报告')}\n")
    L.append("## 一、评定对象与方法\n")
    L.append(f"- 被测量：{r.get('measurand','待企业补充')}（单位：{r.get('unit','待企业补充')}）")
    L.append(f"- 标称值：{r.get('nominal','待企业补充')}")
    L.append(f"- 测量程序/设备：{r.get('procedure','待企业补充')}")
    L.append("- 评定方法：GUM（ISO/IEC Guide 98-3 / JCGM 100），A 类统计 + B 类合成")
    L.append("")
    L.append("## 二、A 类标准不确定度\n")
    a = e["A"]
    if a["has"]:
        L.append(f"- 重复测量次数 n = {a['n']}")
        L.append(f"- 算术平均值 x̄ = {a['mean']:.6g} {r.get('unit','')}")
        L.append(f"- 实验标准差 s = {a['s']:.6g}")
        L.append(f"- u_A = s/√n = {a['uA']:.6g} {r.get('unit','')}")
    else:
        L.append("- （未提供有效重复测量列，u_A 记为 0，待企业补充）")
    L.append("")
    L.append("## 三、B 类标准不确定度分量\n")
    L.append("| 来源 | 半宽 a | 分布 | 灵敏度 c | 标准不确定度 u |")
    L.append("|------|--------|------|-----------|----------------|")
    for b in e["B"]:
        L.append(f"| {b['name']} | {b['a']} | {b['formula']} | {b['c']} | {b['u']:.6g} |")
    L.append("")
    L.append("## 四、合成与扩展不确定度\n")
    L.append(f"- 合成标准不确定度 u_c = √[u_A² + Σu_B²] = {e['u_c']:.6g} {r.get('unit','')}")
    L.append(f"- 覆盖因子 k = {e['k']}（约 95% 置信概率）")
    L.append(f"- 扩展不确定度 U = k·u_c = {e['U']:.6g} {r.get('unit','')}")
    if e["mean"] is not None:
        L.append(f"- 测量结果表达：Y = {e['mean']:.6g} ± {e['U']:.6g} {r.get('unit','')} (k={e['k']})")
        if e["rel"] is not None:
            L.append(f"- 相对扩展不确定度：{e['rel']*100:.4g}%")
    L.append("")
    L.append("## 五、结论与说明\n")
    L.append(r.get("conclusion", "（待企业补充；用于合格判定时，将 U 与规范限比较）"))
    L.append("")
    L.append(f"> 报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 主色 {PRIMARY} ｜ 方法 GUM")
    return "\n".join(L)


CSS = """
:root{--primary:#C8102E;--bg:#f8fafc;--card:#ffffff;--ink:#1e293b;--muted:#64748b;--line:#e2e8f0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.7;padding:32px}
.wrap{max-width:1080px;margin:0 auto}
header{text-align:center;padding:28px 0 18px;border-bottom:3px solid var(--primary);margin-bottom:28px}
header h1{font-size:26px;letter-spacing:1px;color:var(--primary)}
header .meta{color:var(--muted);font-size:14px;margin-top:10px}
.sec{background:var(--card);border-radius:14px;padding:24px;box-shadow:0 4px 16px rgba(0,0,0,.06);margin-bottom:28px}
.sec h2{font-size:21px;margin-bottom:16px;border-left:5px solid var(--primary);padding-left:12px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left}
th{background:#fef2f2;color:var(--primary)}
.kv{font-size:15px;margin:6px 0}
.result{background:#fef2f2;border-left:4px solid var(--primary);padding:14px 18px;border-radius:8px;font-size:16px}
footer{text-align:center;color:var(--muted);font-size:12px;margin-top:20px}
"""


def build_html(r):
    e = evaluate(r)
    a = e["A"]
    if a["has"]:
        a_html = (
            f"<div class='kv'>重复测量次数 n = {a['n']}</div>"
            f"<div class='kv'>算术平均值 x̄ = {a['mean']:.6g} {esc(r.get('unit',''))}</div>"
            f"<div class='kv'>实验标准差 s = {a['s']:.6g}</div>"
            f"<div class='kv'>u_A = s/√n = {a['uA']:.6g} {esc(r.get('unit',''))}</div>"
        )
    else:
        a_html = "<div class='kv' style='color:#64748b'>（未提供有效重复测量列，u_A 记为 0，待企业补充）</div>"

    b_rows = []
    for b in e["B"]:
        b_rows.append(
            f"<tr><td>{esc(b['name'])}</td><td>{b['a']}</td><td>{esc(b['formula'])}</td>"
            f"<td>{b['c']}</td><td>{b['u']:.6g}</td></tr>"
        )
    if not b_rows:
        b_rows.append('<tr><td colspan="5" style="color:#64748b">（暂无 B 类分量，待企业补充）</td></tr>')
    b_html = ("<table><tr><th>来源</th><th>半宽 a</th><th>分布/公式</th><th>灵敏度 c</th><th>标准不确定度 u</th></tr>"
              + "".join(b_rows) + "</table>")

    result = (f"测量结果：Y = {e['mean']:.6g} ± {e['U']:.6g} {esc(r.get('unit',''))} (k={e['k']})"
              if e["mean"] is not None else "（缺 A 类均值）")
    rel_s = f"相对扩展不确定度：{e['rel']*100:.4g}%" if e["rel"] is not None else ""

    return (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(r.get('title','测量不确定度评定报告'))}</title>"
        f"<style>{CSS}</style></head><body><div class='wrap'>"
        f"<header><h1>{esc(r.get('title','测量不确定度评定报告'))}</h1>"
        f"<div class='meta'>被测量：{esc(r.get('measurand','待企业补充'))} ｜ 单位：{esc(r.get('unit','待企业补充'))} ｜ "
        f"方法：GUM（A 类 + B 类合成）</div></header>"
        "<section class='sec'><h2>评定对象与方法</h2>"
        f"<div class='kv'><b>标称值：</b>{esc(r.get('nominal','待企业补充'))}</div>"
        f"<div class='kv'><b>测量程序/设备：</b>{esc(r.get('procedure','待企业补充'))}</div></section>"
        f"<section class='sec'><h2>A 类标准不确定度</h2>{a_html}</section>"
        f"<section class='sec'><h2>B 类标准不确定度分量</h2>{b_html}</section>"
        "<section class='sec'><h2>合成与扩展不确定度</h2>"
        f"<div class='kv'>合成标准不确定度 u_c = {e['u_c']:.6g} {esc(r.get('unit',''))}</div>"
        f"<div class='kv'>覆盖因子 k = {e['k']}（约 95% 置信概率）</div>"
        f"<div class='kv'>扩展不确定度 U = k·u_c = {e['U']:.6g} {esc(r.get('unit',''))}</div>"
        f"<div class='result'>{esc(result)}</div>"
        + (f"<div class='kv' style='margin-top:10px'>{esc(rel_s)}</div>" if rel_s else "")
        + "</section>"
        + f"<section class='sec'><h2>结论与说明</h2><div class='kv'>{esc(r.get('conclusion','（待企业补充；用于合格判定时，将 U 与规范限比较）'))}</div></section>"
        + f"<footer>本报告由 测量不确定度（MU）评定 生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')} · 主色 {PRIMARY}</footer>"
        "</div></body></html>"
    )


SAMPLE = {
    "title": "测量不确定度评定报告（演示样本）",
    "measurand": "某轴径",
    "unit": "mm",
    "nominal": "10.000",
    "procedure": "三坐标测量机 CMM（演示样本，参数待企业补充）",
    "A": {"measurements": [10.012, 10.015, 10.013, 10.014, 10.011, 10.016]},
    "B": [
        {"name": "仪器分辨率", "a": 0.0005, "dist": "rect", "c": 1},
        {"name": "校准不确定度", "a": 0.002, "dist": "norm", "k": 2, "c": 1},
        {"name": "温度影响", "a": 0.0015, "dist": "rect", "c": 1},
    ],
    "k": 2,
    "conclusion": "演示样本：扩展不确定度较小，测量结果可靠；用于合格判定时，将 U 与尺寸公差限比较（实际判定以企业规范为准，待企业补充）。"
}


def main():
    ap = argparse.ArgumentParser(description="测量不确定度评定报告生成器")
    ap.add_argument("--input", help="结构化结果 JSON 路径")
    ap.add_argument("--md-out", default="demo_mu.md", help="输出 MD 路径")
    ap.add_argument("--html-out", default="demo_mu.html", help="输出 HTML 路径")
    ap.add_argument("--demo", action="store_true", help="使用内置小样本生成演示报告")
    args = ap.parse_args()

    if args.demo:
        r = SAMPLE
    elif args.input:
        try:
            r = load_result(args.input)
        except Exception as e:
            sys.stderr.write(f"读取输入失败：{e}\n")
            sys.exit(1)
    else:
        sys.stderr.write("请使用 --input <json> 或 --demo。\n")
        sys.exit(1)

    with open(args.md_out, "w", encoding="utf-8") as f:
        f.write(build_md(r))
    sys.stderr.write(f"MD 已生成：{args.md_out}\n")
    with open(args.html_out, "w", encoding="utf-8") as f:
        f.write(build_html(r))
    sys.stderr.write(f"HTML 已生成：{args.html_out}\n")


if __name__ == "__main__":
    main()
