r"""从 `research/notes/bibliography.md` 生成 `paper/latex/refs.bib`。

**为什么是生成而不是手写**：仓库硬约束规定 `research/notes/bibliography.md` 是文献事实的
**唯一来源**（「未登记即引用＝缺陷」）。手写 .bib 会立刻产生第二份事实，两边必然漂移。
故 .bib 是**派生产物**：改文献 → 重跑本脚本。

映射规则（保证可追溯）：
    md 里的第 N 条  ->  BibTeX key `bibN_<首作者姓><年份>`  ->  正文用 \cite{bibN_...}
    正文中的 `[bib#N]` 与本 key 一一对应。

缺 DOI 的条目不写入（规则 1：每条的必须有 DOI 或稳定链接），并在报告里点名。

用法： .venv/Scripts/python.exe scripts/make_bib.py [--check]
       --check 只校验不写文件（CI/门禁用）
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from evogenesis.experiment.console import force_utf8_stdout

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research" / "notes" / "bibliography.md"
OUT = ROOT / "paper" / "latex" / "refs.bib"

#: `N. Authors. **Title.** *Venue* vol(issue), pages (year). \`status\`.`
#: 三种条目格式（bibliography.md 实际混用；**一个都不许静默丢**）
#: A: `N. Authors. **Title.** *Venue* vol, pages (year). \`status\`.`
RE_A = re.compile(r"^(?P<num>\d+)\.\s+(?P<authors>.+?)\.\s+\*\*(?P<title>.+?)\*\*\s*(?P<rest>.*)$")
#: B: `N. Title (Author Year). \`status\`.`
RE_B = re.compile(
    r"^(?P<num>\d+)\.\s+(?P<title>.+?)\s+\((?P<author_year>[^()]*?)\s*"
    r"(?P<year>(?:19|20)\d{2})\)\.?\s*(?P<rest>.*)$"
)
#: C: 无 `**` 的兜底（仓库 / 专著条目）
RE_C = re.compile(r"^(?P<num>\d+)\.\s+(?P<title>.+?)\.\s*(?P<rest>.*)$")

DOI_RE = re.compile(r"DOI:\s*(?P<doi>\S+)")
LINK_RE = re.compile(r"链接:\s*(?P<url>https?://\S+)")
YEAR_RE = re.compile(r"\((?P<year>(?:19|20)\d{2})\)")
VENUE_RE = re.compile(r"\*(?P<venue>[^*]+)\*")
VOLPAGES_RE = re.compile(r"^(?P<vol>\d+)(?:\((?P<issue>[^)]*)\))?(?:,\s*(?P<pages>[^()]+?))?\s*$")
STATUS_RE = re.compile(r"`(?P<status>[^`]+)`")

_MAP = str.maketrans(
    {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ö": "o",
        "ü": "u",
        "å": "a",
        "ø": "o",
        "ñ": "n",
        "ç": "c",
    }
)


def _tex_escape(text: str) -> str:
    """转义 BibTeX 字段值里对 LaTeX 有特殊含义的字符。

    `.bbl` 里出现的 `#`/`&` 会直接让 LaTeX 报「You can not use macro parameter
    character #」并中止编译 —— 这是生成器必须自己处理的，不能指望手改。
    """
    out = text
    for ch in "#" + chr(38) + "%" + chr(36):
        out = out.replace(ch, "\\" + ch)
    return out


def _ascii_key(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower().translate(_MAP))


def _authors_bibtex(raw: str) -> str:
    """`Zador AM, Barabási DL, et al.` -> `Zador, A. M. and Barabási, D. L. and others`。"""
    raw = raw.strip().rstrip(".")
    et_al = bool(re.search(r"\bet al\.?$", raw))
    raw = raw.replace(" & ", " and ")  # 源文件用 & 连接作者，BibTeX 用 and
    raw = re.sub(r",?\s*et al\.?$", "", raw)
    out = []
    for chunk in [c.strip() for c in raw.split(",") if c.strip()]:
        parts = chunk.split()
        if len(parts) >= 2 and re.fullmatch(r"[A-ZÁÉÍÓÚÄÖÜ]", parts[-1]):
            out.append(f"{' '.join(parts[:-1])}, {parts[-1]}.")
        else:
            out.append(chunk)
    if et_al:
        out.append("others")
    return " and ".join(out)


def _first_surname(raw: str) -> str:
    first = raw.split(",")[0].strip()
    parts = first.split()
    return parts[0] if parts else "anon"


def _classify(title: str, rest: str, window: str) -> tuple[str, str]:
    """返回 (bibtex 类型, 额外字段说明)。三类：仓库 / 专著 / 期刊会议。"""
    blob = rest + window
    if "开源实现" in blob or "GitHub" in title or re.match(r"^[\w.\-]+/[\w.\-]+$", title.strip()):
        return "misc", "GitHub repository"
    if "学术专著" in blob or "非期刊同行评审" in blob:
        return "book", ""
    if "*" in rest and not re.search(r"\*\s*(?:Addison|Princeton|MIT Press|Springer|Wiley)", rest):
        return "article", ""
    return "misc", ""


def parse(text: str) -> tuple[list[dict], list[str]]:
    """返回 (可用条目, 跳过原因)。三种格式依次尝试。"""
    lines = text.split(chr(10))
    entries: list[dict] = []
    skipped: list[str] = []
    seen: set[int] = set()
    for i, line in enumerate(lines):
        m = RE_A.match(line) or RE_B.match(line) or RE_C.match(line)
        if not m:
            continue
        num = int(m.group("num"))
        if num in seen:
            continue
        window = chr(10).join(lines[i : i + 4])
        doi_m = DOI_RE.search(window)
        link_m = LINK_RE.search(window)
        if not (doi_m or link_m):  # 规则 1：DOI **或**稳定链接，二者必居其一
            skipped.append(f"#{num} 既无 DOI 也无链接：{m.group('title')[:46]}")
            continue
        if "authors" in m.groupdict() and m.group("authors"):
            authors = m.group("authors")
            venue_m = VENUE_RE.search(m.group("rest"))
            venue = venue_m.group("venue").strip() if venue_m else ""
            year_m = YEAR_RE.search(m.group("rest"))
            year = year_m.group("year") if year_m else "n.d."
        else:
            # 格式 B 的括号是「作者, 会议, 年份」：末段是**会议名**，不是作者。
            parts = [
                x.strip() for x in (m.groupdict().get("author_year") or "").split(",") if x.strip()
            ]
            if len(parts) > 1:
                authors, venue = ", ".join(parts[:-1]), parts[-1]
            else:
                authors, venue = (parts[0] if parts else "unknown"), ""
            year = m.groupdict().get("year") or "n.d."
        status_m = STATUS_RE.search(m.group("rest")) or STATUS_RE.search(window)
        kind, extra = _classify(m.group("title"), m.group("rest"), window)
        entries.append(
            {
                "num": num,
                "authors": authors,
                "title": m.group("title").strip().rstrip("."),
                "venue": venue,
                "rest": m.group("rest"),
                "year": year,
                "doi": (doi_m.group("doi").rstrip(".,") if doi_m else ""),
                "url": (link_m.group("url").rstrip(".,") if link_m else ""),
                "status": status_m.group("status") if status_m else "unknown",
                "kind": kind,
                "kind_note": extra,
            }
        )
        seen.add(num)
    entries.sort(key=lambda e: e["num"])
    return entries, skipped


def to_bibtex(items: list[dict]) -> str:
    chunks = [
        "% 本文件由 scripts/make_bib.py 从 research/notes/bibliography.md **自动生成**，请勿手改。",
        "% 唯一来源 = research/notes/bibliography.md（AGENTS 硬约束：未登记即引用＝缺陷）。",
        "% key 规则：bibN_<首作者姓><年份>，与 bibliography.md 的第 N 条一一对应。",
        "",
    ]
    for e in items:
        key = f"bib{e['num']}_{_ascii_key(_first_surname(e['authors']))}{e['year']}"
        fields = [
            ("author", _tex_escape(_authors_bibtex(e["authors"]))),
            ("title", "{" + _tex_escape(e["title"]) + "}"),
        ]
        if e["kind"] == "article":
            if e["venue"]:
                fields.append(("journal", "{" + _tex_escape(e["venue"]) + "}"))
            vp = VOLPAGES_RE.match(e["rest"].split("(")[0].strip().lstrip("*").strip())
            if vp:
                if vp.group("vol"):
                    fields.append(("volume", vp.group("vol")))
                if vp.group("issue"):
                    fields.append(("number", vp.group("issue")))
                if vp.group("pages"):
                    pages = vp.group("pages").strip().rstrip(".,")
                    if pages:
                        fields.append(("pages", pages))
        elif e["kind"] == "book":
            fields.append(("publisher", "{" + _tex_escape(e["venue"] or "unknown") + "}"))
        else:
            # 会议名若解析到了就保留（如 CVPR / ICML），否则退回通用说明。
            _where = e["venue"] or e["kind_note"] or "misc"
            fields.append(("howpublished", "{" + _tex_escape(_where) + "}"))
        fields.append(("year", e["year"]))
        if e["doi"]:
            fields.append(("doi", e["doi"]))
        if e["url"]:
            fields.append(("url", "{" + "\\" + "url{" + e["url"] + "}}"))
        fields.append(
            ("note", _tex_escape(f"{e['status']}; evogenesis bibliography.md #{e['num']}"))
        )
        body = ",\n".join(f"  {k:12s} = {{{v}}}" for k, v in fields)
        chunks.append("@" + e["kind"] + "{" + key + ",\n" + body + "\n}\n")
    return chr(10).join(chunks)


def main() -> None:
    # 本脚本会打印 ✅；被重定向时 stdout 回落到 GBK 会 UnicodeEncodeError。
    force_utf8_stdout()
    ap = argparse.ArgumentParser(description="从 bibliography.md 生成 refs.bib")
    ap.add_argument("--check", action="store_true", help="只校验不写文件")
    args = ap.parse_args()

    text = SRC.read_text(encoding="utf-8")
    items, skipped = parse(text)
    bib = to_bibtex(items)

    print(f"解析到条目      : {len(items)}")
    print(f"跳过（缺 DOI）  : {len(skipped)}")
    for s in skipped[:10]:
        print(f"  - {s}")
    if len(skipped) > 10:
        print(f"  ... 其余 {len(skipped) - 10} 条")

    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != bib:
            raise SystemExit(f"{OUT} 与 bibliography.md 不同步：请重跑 scripts/make_bib.py")
        print("refs.bib 与 bibliography.md 同步 ✅")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(bib, encoding="utf-8", newline=chr(10))
    print(f"已写 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
