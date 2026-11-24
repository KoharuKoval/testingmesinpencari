import os
import re
import csv
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TARGET_DOCS = 320
DATA_DIR = "data"
URLS_CACHE_FILE = os.path.join(DATA_DIR, "candidate_urls.json")
CORPUS_FILE = os.path.join(DATA_DIR, "korpus_finansial.json")
SUMMARY_CSV_FILE = os.path.join(DATA_DIR, "ringkasan_crawling.csv")

PAGINATED_SOURCES = [
    {
        "name": "CNBC MyMoney",
        "url_template": "https://www.cnbcindonesia.com/mymoney/indeks/{page}",
        "pages": range(1, 22),
        "allow_pattern": r"cnbcindonesia\.com/mymoney/\d+"
    },
    {
        "name": "Kompas Perencanaan Keuangan",
        "url_template": "https://www.kompas.com/tag/perencanaan-keuangan?page={page}",
        "pages": range(1, 18),
        "allow_pattern": r"kompas\.com/.*/read/\d+"
    },
    {
        "name": "Kompas Literasi Keuangan",
        "url_template": "https://www.kompas.com/tag/literasi-keuangan?page={page}",
        "pages": range(1, 15),
        "allow_pattern": r"kompas\.com/.*/read/\d+"
    },
    {
        "name": "Detik Perencanaan Keuangan",
        "url_template": "https://www.detik.com/tag/perencanaan-keuangan/?sortby=time&page={page}",
        "pages": range(1, 18),
        "allow_pattern": r"detik\.com/.*/d-\d+"
    },
    {
        "name": "Antara Finansial",
        "url_template": "https://www.antaranews.com/ekonomi/finansial/{page}",
        "pages": range(1, 15),
        "allow_pattern": r"antaranews\.com/berita/\d+"
    }
]

FINANCE_KEYWORDS = {
    "uang", "keuangan", "finansial", "tabungan", "menabung", "investasi", "reksadana",
    "saham", "obligasi", "dana darurat", "gaji", "anggaran", "budget", "utang", "kredit",
    "cicilan", "pinjaman", "pajak", "asuransi", "inflasi", "emas", "deposito", "pemula",
    "modal", "aset", "portofolio", "literasi", "hemat", "pensiun", "bunga", "bank", "kas"
}

NOISE_PREFIXES = (
    "baca juga", "lihat juga", "simak video", "advertisement",
    "scroll to continue", "halaman selanjutnya", "editor:", "penulis:"
)


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    return session


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def harvest_urls(session: requests.Session) -> list[dict]:
    """Tahap 1: Mengumpulkan daftar kandidat URL artikel dari halaman indeks/tag."""
    if os.path.exists(URLS_CACHE_FILE):
        with open(URLS_CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if len(cached) >= TARGET_DOCS:
            print(f"[TAHAP 1] Memuat {len(cached)} kandidat URL dari cache '{URLS_CACHE_FILE}'.")
            return cached

    candidates = []
    seen = set()

    for src in PAGINATED_SOURCES:
        src_count = 0
        pattern = re.compile(src["allow_pattern"])
        print(f"[TAHAP 1] Memindai indeks: {src['name']}...")

        for page in src["pages"]:
            list_url = src["url_template"].format(page=page)
            try:
                resp = session.get(list_url, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "lxml")

                for a_tag in soup.find_all("a", href=True):
                    full_url = urljoin(list_url, a_tag["href"]).split("?")[0].split("#")[0]
                    if full_url not in seen and pattern.search(full_url):
                        seen.add(full_url)
                        candidates.append({
                            "url": full_url,
                            "source": src["name"]
                        })
                        src_count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  [WARN] Halaman {page} gagal ({e})")

        print(f"  -> Ditemukan {src_count} URL baru dari {src['name']}.")

    with open(URLS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    print(f"[TAHAP 1 SELESAI] Total kandidat unik: {len(candidates)} URL.\n")
    return candidates


def extract_article_data(session: requests.Session, url: str) -> tuple[str, str, str]:
    """Tahap 2: Mengekstrak judul, tanggal publikasi, dan isi artikel bersih."""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    date_str = ""
    meta_date = (
        soup.find("meta", property="article:published_time")
        or soup.find("meta", attrs={"name": "publishdate"})
        or soup.find("meta", attrs={"name": "date"})
    )
    if meta_date and meta_date.get("content"):
        date_str = meta_date["content"].strip()[:10]

    for noise in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]):
        noise.decompose()

    h1 = soup.find("h1")
    title = clean_text(h1.get_text()) if h1 else ""
    if not title and soup.title:
        title = clean_text(soup.title.get_text())

    container = (
        soup.select_one("div.detail_text")
        or soup.select_one("div.read__content")
        or soup.select_one("div.detail__body-text")
        or soup.select_one("div.post-content")
        or soup.find("article")
        or soup
    )

    paragraphs = []
    for p in container.find_all("p"):
        text = clean_text(p.get_text())
        lower = text.lower()
        if len(text.split()) >= 7 and not lower.startswith(NOISE_PREFIXES):
            paragraphs.append(text)

    content = " ".join(paragraphs)
    return title, date_str, content


def is_valid_financial_doc(title: str, content: str) -> bool:
    if not title or len(content.split()) < 100:
        return False
    sample = f"{title} {content[:600]}".lower()
    score = sum(1 for kw in FINANCE_KEYWORDS if kw in sample)
    return score >= 2


def save_outputs(corpus: list[dict]):
    with open(CORPUS_FILE, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    with open(SUMMARY_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["doc_id", "title", "source", "date", "word_count", "url"])
        for doc in corpus:
            writer.writerow([
                doc["doc_id"], doc["title"], doc["source"],
                doc["date"], doc["word_count"], doc["url"]
            ])


def print_crawling_report(corpus: list[dict], total_attempted: int):
    source_counts = {}
    word_counts = []
    for doc in corpus:
        src = doc["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
        word_counts.append(doc["word_count"])

    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    print("\n" + "=" * 65)
    print("LAPORAN STATISTIK HASIL CRAWLING KORPUS FINANSIAL")
    print("=" * 65)
    print(f"Total URL Diproses       : {total_attempted}")
    print(f"Total Dokumen Valid      : {len(corpus)} dokumen (Target >= 300)")
    print(f"Rata-rata Panjang Teks   : {avg_words:.1f} kata/dokumen")
    if word_counts:
        print(f"Min / Max Kata           : {min(word_counts)} / {max(word_counts)} kata")
    print("-" * 65)
    print("Distribusi Sumber Artikel:")
    for src, cnt in source_counts.items():
        print(f"  - {src:<30}: {cnt} dokumen")
    print("=" * 65)
    print(f"File Korpus JSON         : {CORPUS_FILE}")
    print(f"File Rekap CSV (Laporan) : {SUMMARY_CSV_FILE}\n")


def run_scraper():
    os.makedirs(DATA_DIR, exist_ok=True)
    session = create_session()

    corpus = []
    seen_urls = set()
    seen_titles = set()

    if os.path.exists(CORPUS_FILE):
        with open(CORPUS_FILE, "r", encoding="utf-8") as f:
            corpus = json.load(f)
            seen_urls = {d["url"] for d in corpus}
            seen_titles = {d["title"].lower() for d in corpus}
        print(f"[RESUME] Melanjutkan dari {len(corpus)} dokumen tersimpan.")

    candidates = harvest_urls(session)
    attempted = 0

    print("[TAHAP 2] Memulai ekstraksi konten artikel...")
    for item in candidates:
        if len(corpus) >= TARGET_DOCS:
            break

        url = item["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        attempted += 1

        try:
            title, date_str, content = extract_article_data(session, url)
            norm_title = title.lower()

            if norm_title not in seen_titles and is_valid_financial_doc(title, content):
                seen_titles.add(norm_title)
                doc_id = str(len(corpus) + 1)
                word_count = len(content.split())

                corpus.append({
                    "doc_id": doc_id,
                    "title": title,
                    "url": url,
                    "source": item["source"] or urlparse(url).netloc,
                    "date": date_str,
                    "word_count": word_count,
                    "content": content
                })
                print(f"[{len(corpus):03d}/{TARGET_DOCS}] {item['source']} | {title[:58]}... ({word_count} kata)")

                if len(corpus) % 25 == 0:
                    save_outputs(corpus)

            time.sleep(0.35)
        except Exception:
            continue

    save_outputs(corpus)
    print_crawling_report(corpus, attempted)


if __name__ == "__main__":
    run_scraper()