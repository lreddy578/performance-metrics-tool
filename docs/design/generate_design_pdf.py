from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import markdown


DESIGN_DIR = Path(__file__).parent
MARKDOWN_PATH = DESIGN_DIR / "DESIGN_DOCUMENT.md"
PDF_PATH = DESIGN_DIR / "Performance_Metrics_Tool_Design_Document.pdf"
HTML_PATH = DESIGN_DIR / ".design_document_print.html"

CHROME_PATHS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)


def get_chrome_path() -> Path:
    for path in CHROME_PATHS:
        if path.exists():
            return path
    chrome = shutil.which("chrome")
    if chrome:
        return Path(chrome)
    raise RuntimeError("Google Chrome is required to generate the design PDF.")


def main() -> None:
    body = markdown.markdown(
        MARKDOWN_PATH.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code"],
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Achiever's Scorecard - Design Document</title>
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ color: #172b4d; font: 10.5pt "Segoe UI", sans-serif; line-height: 1.45; }}
  h1 {{ color: #0052cc; font-size: 24pt; margin: 0 0 12pt; }}
  h2 {{ color: #0052cc; border-bottom: 1px solid #dfe1e6; font-size: 16pt; margin-top: 24pt; padding-bottom: 4pt; }}
  h3 {{ font-size: 12pt; margin-top: 16pt; }}
  table {{ border-collapse: collapse; margin: 12pt 0; width: 100%; }}
  th, td {{ border: 1px solid #dfe1e6; padding: 6pt; text-align: left; vertical-align: top; }}
  th {{ background: #f4f5f7; }}
  code {{ background: #f4f5f7; font-family: Consolas, monospace; padding: 1pt 3pt; }}
  pre {{ background: #f4f5f7; overflow-wrap: break-word; padding: 8pt; white-space: pre-wrap; }}
  img {{ display: block; margin: 12pt auto; max-height: 220mm; max-width: 100%; object-fit: contain; page-break-inside: avoid; }}
  p:has(img) {{ break-before: auto; page-break-inside: avoid; }}
  hr {{ border: 0; border-top: 1px solid #dfe1e6; margin: 20pt 0; }}
</style>
</head>
<body>{body}</body>
</html>"""
    HTML_PATH.write_text(html, encoding="utf-8")
    try:
        subprocess.run(
            [
                str(get_chrome_path()),
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={PDF_PATH}",
                HTML_PATH.as_uri(),
            ],
            check=True,
        )
    finally:
        HTML_PATH.unlink(missing_ok=True)

    print(f"Created: {PDF_PATH}")


if __name__ == "__main__":
    main()