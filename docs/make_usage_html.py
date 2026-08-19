#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 README.md 渲染为 使用说明.html（供 X3 桌面快捷方式直接打开）

单一来源：内容以 README.md 为准，本脚本只是把它转成浏览器可读的样式化 HTML。
用法: python3 docs/make_usage_html.py   （在仓库根目录运行，输出 使用说明.html）
"""
import html
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(BASE, "README.md")
OUT = os.path.join(BASE, "使用说明.html")

CSS = """
body { font-family:"Microsoft YaHei",sans-serif; margin:0; background:#1e1e2e; color:#ddd; line-height:1.7; }
.wrap { max-width:920px; margin:0 auto; padding:24px 20px 60px; }
h1 { color:#fff; border-bottom:2px solid #3498db; padding-bottom:10px; }
h2 { color:#7ec8f7; margin-top:32px; border-left:4px solid #3498db; padding-left:10px; }
h3 { color:#cfd8dc; }
code { background:#2a2a3e; padding:2px 6px; border-radius:4px; font-family:Consolas,monospace; color:#ffd47e; }
pre { background:#27293d; padding:12px 14px; border-radius:8px; overflow-x:auto; font-size:14px; }
pre code { background:none; color:#a5e075; padding:0; }
table { border-collapse:collapse; width:100%; margin:10px 0; }
th,td { border:1px solid #3a3a52; padding:6px 10px; text-align:left; font-size:14px; }
th { background:#2a2a3e; }
li { margin:3px 0; }
a { color:#7ec8f7; }
"""


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def render(md: str) -> str:
    out, code_buf, table_buf = [], [], []
    in_code = False

    def flush_table():
        if not table_buf:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")]
                for r in table_buf]
        # 去掉 |---| 分隔行
        rows = [r for r in rows
                if not all(re.fullmatch(r":?-{3,}:?", c or "-") for c in r)]
        if rows:
            out.append("<table><thead><tr>" +
                       "".join(f"<th>{inline(c)}</th>" for c in rows[0]) +
                       "</tr></thead><tbody>")
            for r in rows[1:]:
                out.append("<tr>" +
                           "".join(f"<td>{inline(c)}</td>" for c in r) +
                           "</tr>")
            out.append("</tbody></table>")
        table_buf.clear()

    for line in md.splitlines():
        if line.strip().startswith("```"):
            flush_table()
            if in_code:
                out.append("<pre>" + html.escape("\n".join(code_buf)) + "</pre>")
                code_buf.clear()
            in_code = not in_code
            continue
        if in_code:
            code_buf.append(line)
            continue
        if line.strip().startswith("|"):
            table_buf.append(line)
            continue
        flush_table()
        s = line.strip()
        if not s:
            out.append("")
        elif s.startswith("### "):
            out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("## "):
            out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{inline(s[2:])}</h1>")
        elif s.startswith(("- ", "* ")):
            out.append(f"<li>{inline(s[2:])}</li>")
        elif re.match(r"^\d+\.\s", s):
            out.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', s))}</li>")
        else:
            out.append(f"<p>{inline(s)}</p>")
    flush_table()
    if in_code:
        out.append("<pre>" + html.escape("\n".join(code_buf)) + "</pre>")

    body, buf = [], []
    for item in out:
        if item.startswith("<li>"):
            buf.append(item)
        else:
            if buf:
                body.append("<ul>" + "".join(buf) + "</ul>")
                buf.clear()
            body.append(item)
    if buf:
        body.append("<ul>" + "".join(buf) + "</ul>")
    return "\n".join(body)


def main():
    with open(README, encoding="utf-8") as f:
        md = f.read()
    body = render(md)
    page = ("<!DOCTYPE html>\n<html lang=\"zh\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<title>多模态传感器数据采集 - 使用说明</title>\n<style>" + CSS +
            "</style>\n</head>\n<body><div class=\"wrap\">\n" + body +
            "\n</div></body>\n</html>\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"已生成 {OUT} ({len(page)} 字节)")


if __name__ == "__main__":
    main()
