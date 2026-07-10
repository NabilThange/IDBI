"""
IDBI Bank website scraper -> Markdown knowledge base for RAG.

Strategy:
1. Seed the crawl from https://www.idbi.bank.in/sitemap.aspx, which already
   lists ~90% of the site's real content pages. This avoids wasting time
   crawling menus/login pages/duplicates.
2. Optionally do a shallow recursive crawl (depth-limited) on top of the
   seed list to catch anything the sitemap missed.
3. Convert each page's main content to clean Markdown (nav/header/footer
   stripped) and save one .md file per page.
4. Collect linked PDF URLs separately into pdf_links.txt -- a LOT of the
   bank's real content (interest rates, tariffs, policies, FAQs) lives in
   PDFs, not HTML. Download + text-extract those in a second pass (see
   note at the bottom).

Install deps:
    pip install requests beautifulsoup4 markdownify --break-system-packages

Run:
    python scrape_idbi.py
"""

import re
import time
import queue
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ALLOWED_DOMAIN = "www.idbi.bank.in"
SEED_URLS = [
    "https://www.idbi.bank.in/sitemap.aspx",
    "https://www.idbi.bank.in/index.aspx",
]
OUTPUT_DIR = Path("./idbi_md")
PDF_LIST_FILE = Path("./pdf_links.txt")
MAX_PAGES = 800          # hard cap so a bug can't crawl forever
RECURSE_EXTRA_DEPTH = 1  # how far beyond the sitemap-seeded pages to follow links
REQUEST_DELAY_SEC = 0.6  # be polite / avoid getting rate-limited or blocked
TIMEOUT = 15

# Skip these path fragments (login portals, calculators that need JS/session,
# search endpoints, feedback forms, subdomains that require auth, etc.)
SKIP_PATTERNS = [
    "javascript:", "mailto:", "tel:", "#",
    "login", "logout", "AuthenticationController",
    "ebanking.", "corp.", "inet.", "samriddhi", "clms.", "secureonline",
    "icnrm.", "nri.idbibank", "otsapplication", "pmjjbypmsby",
    "linkaadhaar", "unauthorisedtran", "ifinpro",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RAG-KB-builder/1.0; contact: you@example.com)"
}

session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_same_domain(url: str) -> bool:
    return urlparse(url).netloc == ALLOWED_DOMAIN


def should_skip(url: str) -> bool:
    low = url.lower()
    return any(p.lower() in low for p in SKIP_PATTERNS)


def normalize(url: str) -> str:
    # drop fragments, trailing slash noise
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def slugify(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path) or "index"
    return slug.strip("-").lower()[:150]


def extract_main_content(soup: BeautifulSoup) -> BeautifulSoup:
    # Strip obvious chrome
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    # Try common content containers first; fall back to body
    for selector in ["main", "#content", ".content", ".main-content", "article", "body"]:
        node = soup.select_one(selector)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    return soup.body or soup


def fetch(url: str):
    try:
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        return resp, ctype
    except requests.RequestException as e:
        print(f"  [fail] {url} -> {e}")
        return None, None


def save_markdown(url: str, title: str, content_html) -> None:
    slug = slugify(url)
    out_path = OUTPUT_DIR / f"{slug}.md"
    markdown_body = md(str(content_html), heading_style="ATX")
    # collapse excessive blank lines
    markdown_body = re.sub(r"\n{3,}", "\n\n", markdown_body).strip()
    frontmatter = f"---\ntitle: {title}\nsource_url: {url}\n---\n\n"
    out_path.write_text(frontmatter + markdown_body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main crawl
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    visited = set()
    pdf_links = set()
    q = queue.Queue()

    for seed in SEED_URLS:
        q.put((seed, 0))

    pages_saved = 0

    while not q.empty() and pages_saved < MAX_PAGES:
        url, depth = q.get()
        url = normalize(url)
        if url in visited or should_skip(url) or not is_same_domain(url):
            continue
        visited.add(url)

        print(f"[{pages_saved+1}] fetching {url}")
        resp, ctype = fetch(url)
        time.sleep(REQUEST_DELAY_SEC)
        if resp is None:
            continue

        if url.lower().endswith(".pdf") or "application/pdf" in ctype:
            pdf_links.add(url)
            continue

        if "text/html" not in ctype:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        content = extract_main_content(soup)
        if content and len(content.get_text(strip=True)) > 150:
            save_markdown(url, title, content)
            pages_saved += 1

        # Queue links: always follow links found on seed pages (sitemap/home),
        # otherwise respect RECURSE_EXTRA_DEPTH
        follow_links = (url in [normalize(s) for s in SEED_URLS]) or (depth < RECURSE_EXTRA_DEPTH)
        if follow_links:
            for a in soup.find_all("a", href=True):
                link = urljoin(url, a["href"])
                link = normalize(link)
                if link.lower().endswith(".pdf"):
                    if is_same_domain(link):
                        pdf_links.add(link)
                    continue
                if is_same_domain(link) and not should_skip(link) and link not in visited:
                    q.put((link, depth + 1))

    PDF_LIST_FILE.write_text("\n".join(sorted(pdf_links)), encoding="utf-8")

    print(f"\nDone. Saved {pages_saved} markdown pages to {OUTPUT_DIR}/")
    print(f"Found {len(pdf_links)} PDF links -> {PDF_LIST_FILE} (download/OCR these separately)")


if __name__ == "__main__":
    main()