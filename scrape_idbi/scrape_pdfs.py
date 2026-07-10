"""
One-shot: download all PDFs listed in pdf_links.txt, then convert each to
a clean Markdown file for the RAG knowledge base.

Expected layout (paths are relative to THIS script's location, so it
doesn't matter what folder you run it from):

    C:\\Users\\thang\\Downloads\\IDBI\\scrape_idbi\\
        scrape_pdfs.py        <- this file
        pdf_links.txt         <- one PDF URL per line (put this here first)
        idbi_pdfs\\             <- downloaded PDFs (created automatically)
        idbi_md\\               <- output markdown files (created automatically)

Install deps (Windows, PowerShell/cmd):
    pip install requests pytesseract pillow --break-system-packages

    Also install (these are system tools, not pip packages):
    - Poppler for Windows:  https://github.com/oschwartz10612/poppler-windows/releases
        -> unzip, add its "bin" folder to your PATH (gives you pdftotext,
           pdfinfo, pdftoppm)
    - Tesseract OCR:        https://github.com/UB-Mannheim/tesseract/wiki
        -> install, add its install folder to your PATH (gives you tesseract)

    Quick check both are on PATH:
        pdftotext -v
        tesseract -v

Run:
    python scrape_pdfs.py
"""

import re
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ---------------------------------------------------------------------------
# Config -- all paths anchored to this script's folder
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
LINKS_FILE = BASE_DIR / "pdf_links.txt"
PDF_DIR = BASE_DIR / "idbi_pdfs"
OUT_DIR = BASE_DIR / "idbi_md"
TMP_OCR_DIR = BASE_DIR / "_ocr_tmp"

MAX_WORKERS = 8
MAX_RETRIES = 3
TIMEOUT = 30
MIN_CHARS_PER_PAGE = 40   # below this average, assume scanned -> OCR
OCR_DPI = 200

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RAG-KB-builder/1.0; contact: you@example.com)"
}


# ---------------------------------------------------------------------------
# Step 1: bulk download
# ---------------------------------------------------------------------------
def filename_for(url: str) -> str:
    name = Path(urlparse(url).path).name
    return name.replace(" ", "-")


def download_one(url: str) -> tuple[str, bool, str]:
    dest = PDF_DIR / filename_for(url)
    if dest.exists() and dest.stat().st_size > 0:
        return url, True, "already exists"

    last_err = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return url, True, f"ok ({len(resp.content)} bytes)"
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(1.5 * attempt)
    return url, False, last_err


def bulk_download(urls: list[str]) -> list[str]:
    PDF_DIR.mkdir(exist_ok=True)
    print(f"--- Step 1/2: downloading {len(urls)} PDFs into {PDF_DIR} ---\n")

    failures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(download_one, url): url for url in urls}
        for i, future in enumerate(as_completed(futures), 1):
            url, ok, msg = future.result()
            print(f"[{i}/{len(urls)}] {'OK' if ok else 'FAIL':4} {url} -> {msg}")
            if not ok:
                failures.append(url)

    print(f"\nDownload done. {len(urls) - len(failures)}/{len(urls)} succeeded.")
    if failures:
        fail_file = BASE_DIR / "pdf_download_failures.txt"
        fail_file.write_text("\n".join(failures), encoding="utf-8")
        print(f"{len(failures)} failed -> logged to {fail_file}")
    return failures


# ---------------------------------------------------------------------------
# Step 2: convert each downloaded PDF -> markdown
# ---------------------------------------------------------------------------
def page_count(pdf_path: Path) -> int:
    try:
        out = subprocess.run(
            ["pdfinfo", str(pdf_path)], capture_output=True,
            text=True, encoding="utf-8", errors="replace", check=True
        ).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        return int(m.group(1)) if m else 1
    except Exception:
        return 1


def extract_text_layer(pdf_path: Path) -> str:
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60
        )
        return out.stdout or ""
    except Exception as e:
        print(f"  [pdftotext fail] {e}")
        return ""


def ocr_pdf(pdf_path: Path, slug: str) -> str:
    import pytesseract
    from PIL import Image

    work_dir = TMP_OCR_DIR / slug
    work_dir.mkdir(exist_ok=True, parents=True)
    prefix = work_dir / "page"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(OCR_DPI), str(pdf_path), str(prefix)],
        check=True, timeout=180
    )
    text_parts = []
    for img_path in sorted(work_dir.glob("page-*.png")):
        try:
            text_parts.append(pytesseract.image_to_string(Image.open(img_path)))
        except Exception as e:
            print(f"  [ocr fail on {img_path.name}] {e}")
    for img_path in work_dir.glob("page-*.png"):
        img_path.unlink()
    work_dir.rmdir()
    return "\n\n".join(text_parts)


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def convert_all_pdfs() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    pdf_files = sorted(set(PDF_DIR.glob("*.pdf")) | set(PDF_DIR.glob("*.PDF")))
    print(f"\n--- Step 2/2: converting {len(pdf_files)} PDFs to markdown in {OUT_DIR} ---\n")

    for i, pdf_path in enumerate(pdf_files, 1):
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", pdf_path.stem).strip("-").lower()[:150] or "file"
        md_path = OUT_DIR / f"{slug}.md"

        if md_path.exists():
            print(f"[{i}/{len(pdf_files)}] skip (already converted) {pdf_path.name}")
            continue

        print(f"[{i}/{len(pdf_files)}] converting {pdf_path.name}")
        try:
            pages = page_count(pdf_path)
            text = extract_text_layer(pdf_path) or ""
            used_ocr = False

            avg_chars = len(text) / max(pages, 1)
            if avg_chars < MIN_CHARS_PER_PAGE:
                print(f"    -> thin text layer ({avg_chars:.0f} chars/page), running OCR ({pages} pages)")
                text = ocr_pdf(pdf_path, slug)
                used_ocr = True

            text = clean_text(text)
            if not text:
                print(f"    [warn] no text extracted at all")

            frontmatter = (
                f"---\n"
                f"title: {slug}\n"
                f"source_file: {pdf_path.name}\n"
                f"pages: {pages}\n"
                f"ocr_used: {used_ocr}\n"
                f"---\n\n"
            )
            md_path.write_text(frontmatter + text, encoding="utf-8")
            print(f"    saved -> {md_path.name} ({'OCR' if used_ocr else 'text layer'}, {len(text)} chars)")
        except Exception as e:
            print(f"    [ERROR] skipping {pdf_path.name}: {e}")
            continue

    if TMP_OCR_DIR.exists():
        try:
            TMP_OCR_DIR.rmdir()
        except OSError:
            pass  # not empty / in use, harmless to leave


# ---------------------------------------------------------------------------
def main():
    if not LINKS_FILE.exists():
        print(f"ERROR: {LINKS_FILE} not found.")
        print("Create pdf_links.txt next to this script, one PDF URL per line, then rerun.")
        return

    urls = [line.strip() for line in LINKS_FILE.read_text().splitlines() if line.strip()]
    bulk_download(urls)
    convert_all_pdfs()
    print(f"\nAll done. Markdown files are in: {OUT_DIR}")


if __name__ == "__main__":
    main()