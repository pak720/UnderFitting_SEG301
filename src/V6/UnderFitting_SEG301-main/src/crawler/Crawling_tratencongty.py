import random
import requests
import csv
import time
import os
import re
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# ========================
# CẤU HÌNH
# ========================
BASE_DOMAIN = "https://www.tratencongty.com"
OUTPUT_FILE = "Data_tratencongty.csv"

START_PAGE = 351
END_PAGE = 355
START_ROW = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
}

PAGE_SLEEP_MIN = 1.2
PAGE_SLEEP_MAX = 2.5
BATCH_SIZE = 50

EXPECTED_COLS = 7

# ========================
# SESSION
# ========================
session = requests.Session()
session.headers.update(HEADERS)

# ========================
# CSV INIT (KHÔNG HEADER)
# ========================
if not os.path.exists(OUTPUT_FILE):
    open(OUTPUT_FILE, "w").close()

# ========================
# CLEAN FUNCTIONS
# ========================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('""', '"').strip('"')
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_company_name(name: str) -> str:
    name = clean_text(name)
    return re.sub(r"\.\s*$", "", name)


def normalize_date(date_str: str) -> str:
    if not date_str:
        return ""

    date_str = clean_text(date_str)
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
    if not match:
        return date_str

    d, m, y = match.groups()
    return f"{int(d):02d}/{int(m):02d}/{y}"

# ========================
# CRAWL LIST
# ========================
def crawl_list_page(page):
    url = f"{BASE_DOMAIN}/?page={page}"
    print(f"\n[LIST] Page {page}")

    try:
        res = session.get(url, timeout=(5, 10))
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        blocks = soup.select("div.search-results")

        results = []
        for b in blocks:
            a = b.select_one("a[href]")
            if not a:
                continue

            name = a.get_text(strip=True)
            link = a["href"]
            if link.startswith("/"):
                link = BASE_DOMAIN + link

            results.append((name, link))

        return results

    except RequestException:
        return []

# ========================
# CRAWL DETAIL
# ========================
def crawl_detail_page(detail_url, retry=3):
    for _ in range(retry):
        try:
            res = session.get(detail_url, timeout=(5, 15))
            if res.status_code != 200:
                return None

            soup = BeautifulSoup(res.text, "html.parser")
            container = soup.select_one("div.jumbotron")
            if not container:
                return None

            data = {
                "company_name": "",
                "address": "",
                "legal_rep": "",
                "license_date": "",
                "active_date": "",
                "status": ""
            }

            h4 = container.find("h4")
            if h4:
                data["company_name"] = h4.get_text(strip=True)

            raw = container.get_text(separator="\n")
            lines = [l.strip() for l in raw.split("\n") if l.strip()]

            for line in lines:
                if line.startswith("Địa chỉ"):
                    data["address"] = line.replace("Địa chỉ:", "").strip()
                elif line.startswith("Đại diện pháp luật"):
                    data["legal_rep"] = line.replace("Đại diện pháp luật:", "").strip()
                elif line.startswith("Ngày cấp giấy phép"):
                    data["license_date"] = line.replace("Ngày cấp giấy phép:", "").strip()
                elif line.startswith("Ngày hoạt động"):
                    data["active_date"] = line.replace("Ngày hoạt động:", "").strip()
                elif line.startswith("Trạng thái"):
                    data["status"] = line.replace("Trạng thái:", "").strip()

            if not data["company_name"]:
                return None

            return data

        except RequestException:
            time.sleep(1)

    return None

# ========================
# MAIN
# ========================
global_row = 0
buffer = []

with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)

    for page in range(START_PAGE, END_PAGE + 1):
        companies = crawl_list_page(page)
        if not companies:
            break

        for name, link in companies:
            if global_row < START_ROW:
                global_row += 1
                continue

            detail = crawl_detail_page(link)
            if not detail:
                global_row += 1
                continue

            row = [
                clean_company_name(detail["company_name"] or name),
                clean_text(detail["address"]),
                clean_text(detail["legal_rep"]),
                normalize_date(detail["license_date"]),
                normalize_date(detail["active_date"]),
                clean_text(detail["status"]),
                link
            ]

            if len(row) == EXPECTED_COLS:
                buffer.append(row)

            global_row += 1

            if len(buffer) >= BATCH_SIZE:
                writer.writerows(buffer)
                buffer.clear()
                print("💾 Batch saved")

        time.sleep(random.uniform(PAGE_SLEEP_MIN, PAGE_SLEEP_MAX))

    if buffer:
        writer.writerows(buffer)

print("✅ DONE – data crawl ra đã CLEAN SẴN")
