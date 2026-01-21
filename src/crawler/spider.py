# crawler/spider.py
import aiohttp
import asyncio
import csv
import os
import random
from bs4 import BeautifulSoup

from .utils import (
    BASE_URL, OUTPUT_FILE,
    START_PAGE, END_PAGE,
    NUM_WORKERS, QUEUE_SIZE, BATCH_SIZE,
    FIELDNAMES, HEADERS, fetch_html
)
from .parser import parse_company_page

# ========================
# PRODUCER
# ========================
async def produce_links(session, queue):
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
                full_url = (
                    href if href.startswith("http")
                    else "https://infodoanhnghiep.com" + href
                )
                await queue.put(full_url)

# ========================
# WORKER
# ========================
async def worker(worker_id, session, queue, buffer, buffer_lock):
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
                    writer = csv.DictWriter(
                        f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL
                    )
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
            writer = csv.DictWriter(
                f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL
            )
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
            writer = csv.DictWriter(
                f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL
            )
            writer.writerows(buffer)

    print("✅ HOÀN THÀNH")

if __name__ == "__main__":
    asyncio.run(main())
