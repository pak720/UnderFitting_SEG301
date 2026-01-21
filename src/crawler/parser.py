# crawler/parser.py
from bs4 import BeautifulSoup
from typing import Dict
from .utils import FIELDNAMES, clean_text

def parse_company_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    data = {k: "" for k in FIELDNAMES}
    data["url"] = url

    def get_text(el):
        return clean_text(el.get_text(strip=True)) if el else ""

    data["ten_doanh_nghiep"] = get_text(
        soup.select_one("div.m-panel-heading.main-heading h1")
        or soup.select_one('div[itemprop="name"] h3')
    )
    data["ma_so_thue"] = get_text(soup.select_one('div[itemprop="taxID"]'))
    data["dia_chi"] = get_text(soup.select_one('div[itemprop="address"]'))

    cells = soup.select("div.responsive-table-cell")
    for i in range(len(cells) - 1):
        label = cells[i].get_text(strip=True)
        value = cells[i + 1].get_text(strip=True)

        if label == "Tên giao dịch":
            data["ten_giao_dich"] = clean_text(value)
        elif "Ngày cấp giấy phép" in label:
            data["ngay_cap"] = clean_text(value)
        elif "Tình trạng hoạt động" in label:
            data["tinh_trang"] = clean_text(value)

    for cell in soup.select("div.nnkd-table div.responsive-table-cell"):
        text = cell.get_text(strip=True)
        if "(Ngành chính)" in text:
            data["linh_vuc"] = clean_text(
                text.replace("(Ngành chính)", "")
            )
            break

    return data
