"""Render docs/readout.md (the one-page memo) as a print-friendly reports/memo.html."""
from __future__ import annotations

import markdown

from src.config import ROOT

SRC = ROOT / "docs" / "readout.md"
OUT = ROOT / "reports" / "memo.html"

CSS = """
body{margin:0;background:#fcfcfb;color:#0b0b0b;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.page{max-width:760px;margin:0 auto;padding:36px 22px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:20px 0 6px} p,li{margin:5px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0} th,td{border-bottom:1px solid #e1e0d9;padding:5px 6px;text-align:left;vertical-align:top}
th{color:#52514e} em{color:#52514e} hr{border:0;border-top:1px solid #e1e0d9;margin:14px 0}
@media print{body{background:#fff}.page{padding:0;max-width:none}}
"""


def build() -> None:
    if not SRC.exists():
        print("    docs/readout.md not found - memo skipped")
        return
    body = markdown.markdown(SRC.read_text(encoding="utf-8"), extensions=["tables"])
    OUT.write_text(f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                   f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                   f"<title>Memo: readmission penalties and the follow-up program</title><style>{CSS}</style></head>"
                   f"<body><div class='page'>{body}</div></body></html>", encoding="utf-8")
    print(f"    wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
