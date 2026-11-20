"""Chuyển đặc tả use case HTT EXPRESS (.docx) sang Markdown.

Cách dùng: python -I docx2md.py <input.docx> <output.md>
"""
import html
import re
import sys
import zipfile

W = r"w:"


def para_text(p):
    out = []
    for m in re.finditer(r"<w:t(?: [^>]*)?>([^<]*)</w:t>|<w:tab/>|<w:br/>", p):
        if m.group(1) is not None:
            out.append(m.group(1))
        elif m.group(0) == "<w:tab/>":
            out.append(" ")
        else:
            out.append(" ")
    return html.unescape("".join(out)).strip()


def para_style(p):
    m = re.search(r'<w:pStyle w:val="([^"]+)"', p)
    return m.group(1) if m else ""


def cell_paras(tc):
    return [t for t in (para_text(p) for p in re.findall(r"<w:p[ >].*?</w:p>", tc, re.S)) if t]


def rows_of(tbl):
    return [
        [cell_paras(tc) for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S)]
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S)
    ]


def esc_cell(s):
    return s.replace("|", "\\|")


def render_grid(rows):
    lines = []
    header = [" ".join(c) for c in rows[0]]
    lines.append("| " + " | ".join(esc_cell(h) for h in header) + " |")
    lines.append("|" + "---|" * len(header))
    for r in rows[1:]:
        lines.append("| " + " | ".join(esc_cell("<br>".join(c)) for c in r) + " |")
    return "\n".join(lines)


STEP = re.compile(r"^(\d+)\.\s+(.*)$")
BRANCH_HEAD = re.compile(r"^([AE]\d+)\s+–\s+(.*)$")
BRANCH_STEP = re.compile(r"^([AE]\d+\.\d+)\.\s+(.*)$")
INLINE_LABELS = {"Mô tả", "Đường dẫn", "Tác nhân", "Điều kiện trước", "Điều kiện sau"}


def render_uc(rows):
    out = []
    for cells in rows:
        if len(cells) != 2 or not cells[0]:
            out.append(render_grid([cells]))
            continue
        label, content = " ".join(cells[0]), cells[1]
        if label == "Tên chức năng":
            continue  # đã có ở tiêu đề
        if label in INLINE_LABELS and len(content) == 1:
            out.append(f"**{label}:** {content[0]}\n")
            continue
        out.append(f"**{label}**\n")
        block = []
        for line in content:
            if m := BRANCH_HEAD.match(line):
                block.append(f"\n- **{m.group(1)} – {m.group(2)}**")
            elif line.startswith("Điều kiện:"):
                block.append(f"  - *{line}*")
            elif m := BRANCH_STEP.match(line):
                block.append(f"  - {m.group(1)}. {m.group(2)}")
            elif m := STEP.match(line):
                block.append(f"{m.group(1)}. {m.group(2)}")
            else:
                block.append(f"- {line}")
        out.append("\n".join(block).lstrip("\n") + "\n")
    return "\n".join(out)


def main(src, dst):
    xml = zipfile.ZipFile(src).read("word/document.xml").decode("utf8")
    body = xml[xml.find("<w:body>") + len("<w:body>"): xml.rfind("</w:body>")]
    md = []
    for m in re.finditer(r"<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>|<w:p/>", body, re.S):
        chunk = m.group(0)
        if chunk.startswith("<w:tbl>"):
            rows = rows_of(chunk)
            ncol = max(len(r) for r in rows)
            md.append(render_grid(rows) if ncol != 2 else render_uc(rows))
            continue
        text = para_text(chunk)
        if not text:
            continue
        style = para_style(chunk)
        if style == "Title":
            md.append(f"# {text}")
        elif style == "Subtitle":
            md.append(f"*{text}*")
        elif style == "Heading1":
            md.append(f"## {text}")
        elif style == "Heading2":
            md.append(f"### {text}")
        elif style == "ListBullet":
            md.append(f"- {text}")
        else:
            md.append(text)
    md.insert(1, "> Bản Markdown xuất tự động từ `HTT_EXPRESS_Dac_ta_42_Use_Case.docx` để đọc và tra cứu khi code. "
                 "File .docx là bản gốc; khi .docx thay đổi, xuất lại file này thay vì sửa tay.")
    result = "\n\n".join(md)
    prev = None
    while prev != result:  # gộp bullet liên tiếp
        prev, result = result, re.sub(r"(\n- [^\n]+)\n\n(?=- )", r"\1\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result).strip() + "\n"
    with open(dst, "w", encoding="utf8", newline="\n") as f:
        f.write(result)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
