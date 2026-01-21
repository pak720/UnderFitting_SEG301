import aiohttp
import asyncio
import csv
import os
import random
import re
from bs4 import BeautifulSoup
from typing import Dict

# ========================
# CẤU HÌNH
# ========================
BASE_URL = "https://infodoanhnghiep.com/Bac-Lieu"
OUTPUT_FILE = "Data_infodoanhnghiep.csv"



START_PAGE = 1
END_PAGE = 318

NUM_WORKERS = 50
QUEUE_SIZE = 500
BATCH_SIZE = 50

FIELDNAMES = [
    "ten_doanh_nghiep",
    "ten_giao_dich",
    "ma_so_thue",
    "dia_chi",
    "tinh_trang",
    "ngay_cap",
    "linh_vuc",
    "url"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
}

# ========================
# CLEAN FUNCTIONS (GIỮ NGUYÊN)
# ========================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('""', '"').strip('"')
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_company_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    data = {k: "" for k in FIELDNAMES}
    data["url"] = url

    def get_text(el):
        return el.get_text(strip=True) if el else ""

    data["ten_doanh_nghiep"] = get_text(
        soup.select_one("div.m-panel-heading.main-heading h1")
        or soup.select_one('div[itemprop="name"] h3')
    )
    data["ma_so_thue"] = get_text(soup.select_one('div[itemprop="taxID"]'))
    data["dia_chi"] = get_text(soup.select_one('div[itemprop="address"]'))

    cells = soup.select("div.responsive-table-cell")
    for i in range(len(cells) - 1):
        label = cells[i].get_text(strip=True)
        if label == "Tên giao dịch":
            data["ten_giao_dich"] = cells[i + 1].get_text(strip=True)
        elif "Ngày cấp giấy phép" in label:
            data["ngay_cap"] = cells[i + 1].get_text(strip=True)
        elif "Tình trạng hoạt động" in label:
            data["tinh_trang"] = cells[i + 1].get_text(strip=True)

    for cell in soup.select("div.nnkd-table div.responsive-table-cell"):
        text = cell.get_text(strip=True)
        if "(Ngành chính)" in text:
            data["linh_vuc"] = text.replace("(Ngành chính)", "").strip()
            break

    return data

# ========================
# FETCH
# ========================
async def fetch_html(session: aiohttp.ClientSession, url: str, retries=3) -> str | None:
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status == 200:
                    return await resp.text()
                if resp.status == 404:
                    return None
        except Exception:
            await asyncio.sleep(attempt * 1.5)
    return None

# ========================
# PRODUCER
# ========================
async def produce_links(session: aiohttp.ClientSession, queue: asyncio.Queue):
    for page in range(START_PAGE, END_PAGE + 1):
        page_url = BASE_URL if page == 1 else f"{BASE_URL}/trang-{page}/"
        print(f"[PAGE {page}] {page_url}")

        html = await fetch_html(session, page_url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("div.company-item h3.company-name a"):
            href = a.get("href")
            if href:
                full_url = href if href.startswith("http") else "https://infodoanhnghiep.com" + href
                await queue.put(full_url)

# ========================
# WORKER
# ========================
async def worker(worker_id: int, session, queue, buffer, buffer_lock):
    while True:
        url = await queue.get()
        if url is None:
            queue.task_done()
            break

        html = await fetch_html(session, url)
        await asyncio.sleep(random.uniform(0.4, 0.9))

        if html:
            try:
                data = parse_company_page(html, url)
                async with buffer_lock:
                    buffer.append(data)
            except Exception as e:
                print(f"[WORKER {worker_id}] ERROR {url}: {e}")

        queue.task_done()

# ========================
# WRITER
# ========================
async def writer_task(buffer, buffer_lock):
    while True:
        await asyncio.sleep(2)
        async with buffer_lock:
            if len(buffer) >= BATCH_SIZE:
                with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
                    writer.writerows(buffer)
                print(f"💾 Đã ghi {len(buffer)} dòng")
                buffer.clear()

# ========================
# MAIN
# ========================
async def main():
    queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    buffer = []
    buffer_lock = asyncio.Lock()

    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
            writer.writeheader()

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        workers = [
            asyncio.create_task(worker(i, session, queue, buffer, buffer_lock))
            for i in range(1, NUM_WORKERS + 1)
        ]

        writer = asyncio.create_task(writer_task(buffer, buffer_lock))

        await produce_links(session, queue)
        await queue.join()

        for _ in workers:
            await queue.put(None)

        await asyncio.gather(*workers)
        writer.cancel()

    if buffer:
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
            writer.writerows(buffer)

    print("✅ HOÀN THÀNH")

if __name__ == "__main__":
    asyncio.run(main())
