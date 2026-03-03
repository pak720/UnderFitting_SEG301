# crawler/utils.py
import aiohttp
import asyncio
import random
import re
from typing import Dict

# ========================
# CONFIG
# ========================
BASE_URL = "https://infodoanhnghiep.com/Binh-Phuoc"
OUTPUT_FILE = "Data_infodoanhnghiep_clean.csv"

START_PAGE = 1
END_PAGE = 686

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
# CLEAN TEXT
# ========================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('""', '"').strip('"')
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ========================
# FETCH HTML
# ========================
async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    retries: int = 3
) -> str | None:
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
