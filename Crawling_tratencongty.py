# ========================
# IMPORT
# ========================
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

START_PAGE = 330
END_PAGE = 335
START_ROW = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
}

PAGE_SLEEP_MIN = 1.2
PAGE_SLEEP_MAX = 2.5
BATCH_SIZE = 50

# ========================
# KHỞI TẠO SESSION
# ========================
session = requests.Session()
session.headers.update(HEADERS)

# ========================
# KHỞI TẠO FILE CSV
# ========================
if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "company_name",
            "mst",
            "address",
            "legal_rep",
            "license_date",
            "active_date",
            "status",
            "detail_link"
        ])

# ========================
# CLEAN TEXT
# ========================
def clean_field(text):
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

# ========================
# CRAWL TRANG LIST
# ========================
def crawl_list_page(page):
    url = f"{BASE_DOMAIN}/?page={page}"
    print(f"\n[LIST] Page {page}")

    try:
        res = session.get(url, timeout=(5, 10))
        if res.status_code != 200:
            print(f"⚠️ HTTP {res.status_code}")
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

        print(f"[INFO] Found {len(results)} companies")
        return results

    except RequestException as e:
        print(f"❌ List error: {e}")
        return []

# ========================
# CRAWL TRANG DETAIL
# ========================
def crawl_detail_page(detail_url, retry=3):
    for attempt in range(1, retry + 1):
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
                "mst": "",
                "address": "",
                "legal_rep": "",
                "license_date": "",
                "active_date": "",
                "status": ""
            }

            name_tag = container.select_one("h4 span[title]")
            if name_tag:
                data["company_name"] = name_tag.get_text(strip=True)
            else:
                h4 = container.find("h4")
                if h4:
                    data["company_name"] = h4.get_text(strip=True)

            raw_text = container.get_text(separator="\n")
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

            for line in lines:
                if "Mã số thuế" in line:
                    data["mst"] = line.replace("Mã số thuế:", "").strip()
                elif line.startswith("Địa chỉ"):
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

with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    for page in range(START_PAGE, END_PAGE + 1):
        companies = crawl_list_page(page)
        if not companies:
            print("⚠️ Empty page → stop")
            break

        for name, link in companies:
            if global_row < START_ROW:
                global_row += 1
                continue

            print(f"[ROW {global_row}] {name}")

            detail = crawl_detail_page(link)
            if not detail:
                global_row += 1
                continue

            row = [
                clean_field(detail.get("company_name") or name),
                clean_field(detail.get("mst")),
                clean_field(detail.get("address")),
                clean_field(detail.get("legal_rep")),
                clean_field(detail.get("license_date")),
                clean_field(detail.get("active_date")),
                clean_field(detail.get("status")),
                clean_field(link)
            ]

            row = [col for col in row if col.strip() != ''] 
            row = [clean_field(col) for col in row]

            buffer.append(row)

            global_row += 1

            if len(buffer) >= BATCH_SIZE:
                writer.writerows(buffer)
                buffer.clear()
                print("💾 Batch saved")

        time.sleep(random.uniform(PAGE_SLEEP_MIN, PAGE_SLEEP_MAX))

    if buffer:
        writer.writerows(buffer)
        print("💾 Final batch saved")

print("✅ DONE")
