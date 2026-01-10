# ========================
# CẤU HÌNH
# ========================
import random
import requests
import csv
import time
import os
import re
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

BASE_DOMAIN = "https://www.tratencongty.com"
OUTPUT_FILE = "Data_tratencongty_clean.csv"

START_PAGE = 157     # page bắt đầu
END_PAGE = 160      # page kết thúc
START_ROW = 0       # resume theo dòng toàn cục

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
}

# ========================# KHỞI TẠO FILE KẾT QUẢ
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
# CRAW TRANG TỔNG
# ========================
def crawl_list_page(page):
    url = f"{BASE_DOMAIN}/?page={page}"
    print(f"\n[LIST] Crawling page {page}: {url}")

    res = requests.get(url, headers=HEADERS, timeout=(5, 10))
    soup = BeautifulSoup(res.text, "html.parser")

    blocks = soup.select("div.search-results")
    print(f"[INFO] Found {len(blocks)} companies")

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


# ========================
# CRAWL TRANG CHI TIẾT
# ========================
def crawl_detail_page(detail_url, retry=3):
    print(f"    ↳ Detail: {detail_url}")

    for attempt in range(1, retry + 1):
        try:
            res = requests.get(
                detail_url,
                headers=HEADERS,
                timeout=(5, 15)
            )

            print(f"      Attempt {attempt} | HTTP {res.status_code}")

            if res.status_code != 200:
                return None

            soup = BeautifulSoup(res.text, "html.parser")

            container = soup.select_one("div.jumbotron")
            if not container:
                print("      ⚠️ jumbotron not found")
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

            # ✅ 1. LẤY TÊN CÔNG TY CHUẨN (KHÔNG DÙNG TEXT LINE)
            name_tag = container.select_one("h4 span[title]")
            if name_tag:
                data["company_name"] = name_tag.get_text(strip=True)
            else:
                # fallback
                h4 = container.find("h4")
                if h4:
                    data["company_name"] = h4.get_text(strip=True)

            # ✅ 2. PARSE TEXT
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

            # ✅ KIỂM TRA DỮ LIỆU TRƯỚC KHI TRẢ
            if not data["company_name"]:
                print("      ⚠️ Missing company name → skip")
                return None

            return data

        except RequestException as e:
            print(f"      ❌ Attempt {attempt} failed: {e}")
            time.sleep(2)

    print("      ❌ Failed after retries")
    return None

#=========================
# CLEAN TEXT
#=========================
def clean_field(text):
    if not text:
        return ""

    text = text.strip()
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"\s+", " ", text)

    return text

# ========================
# CHƯƠNG TRÌNH CHÍNH
# ========================
global_row = 0

with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    for page in range(START_PAGE, END_PAGE + 1):
        companies = crawl_list_page(page)

        if not companies:
            print("⚠️ No companies → stop")
            break

        for name, link in companies:

            if global_row < START_ROW:
                global_row += 1
                continue

            print(f"[PAGE {page} | ROW {global_row}] {name}")

            detail = crawl_detail_page(link)

            if not detail:
                print("    ⚠️ Skip CSV")
                global_row += 1
                continue

            # Tạo row ban đầu
            row = [
                detail.get("company_name") or name,
                detail.get("mst", ""),
                detail.get("address", ""),
                detail.get("legal_rep", ""),
                detail.get("license_date", ""),
                detail.get("active_date", ""),
                detail.get("status", ""),
                clean_field(link)
            ]

            # Lọc bỏ cột trống
            row = [col for col in row if col.strip() != '']
            row = [clean_field(col) for col in row]

            # Ghi row đã lọc vào CSV
            writer.writerow(row)

            print("    ✅ Saved")
            global_row += 1
            time.sleep(0.5 + random.uniform(0, 0.3))
