import asyncio
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import requests
import aiohttp

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.service import Service as EdgeService
from bs4 import BeautifulSoup
import os

# Danh sách URL các công ty cần crawl
COMPANY_URLS = [
    "https://thongtincongty.vn/ma-so-thue/096194012636-ho-kinh-doanh-nha-thuoc-y-duc-sai-gon-duong-vo-van-kiet-ap-tac-thu-562387281",
    # Thêm các URL khác vào đây
]

def norm_text(s: str) -> str:
    """Chuẩn hóa text: loại bỏ khoảng trắng dư thừa"""
    return re.sub(r"\s+", " ", (s or "")).strip()

def get_company_links_from_homepage(max_links=10, max_pages=5):
    """Lấy danh sách link công ty từ trang chủ.

    Trang chủ hiện chỉ có trang 1, các trang /page/2/ bị 404. Nếu thiếu link
    sẽ tự động bổ sung bằng tìm kiếm với các từ khóa phổ biến để gom thêm công ty.
    """
    print("\n🔍 Đang lấy danh sách công ty từ trang chủ...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        links = []

        for page in range(1, max_pages + 1):
            url = "https://thongtincongty.vn/" if page == 1 else f"https://thongtincongty.vn/page/{page}/"
            resp = requests.get(url, headers=headers, timeout=30)

            # Trang /page/2/ trả về 404, dừng vòng lặp sớm để tránh lỗi
            if resp.status_code == 404 and page > 1:
                print(f"  ⚠️ Trang {url} trả về 404, dừng phân trang trang chủ.")
                break

            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/ma-so-thue/' in href:
                    full_url = href if href.startswith('http') else f"https://thongtincongty.vn{href}"
                    if full_url not in links:
                        links.append(full_url)
                    if len(links) >= max_links:
                        break
            if len(links) >= max_links:
                break
            # nhỏ delay giữa trang
            time.sleep(0.1)

        # Nếu thiếu link, fallback sang tìm kiếm với bộ từ khóa phổ biến
        if len(links) < max_links:
            print("  ℹ️ Trang chủ không đủ, chuyển sang tìm kiếm để bổ sung link...")
            keyword_pool = [
                "a", "e", "i", "o", "u", "1", "2", "3", "c", "t",
                "công ty", "doanh nghiệp", "tập đoàn", "cửa hàng", "chi nhánh",
                "văn phòng", "nhà hàng", "quán", "bưu cục", "trạm",
                "siêu thị", "khách sạn", "công xưởng", "kho", "trung tâm"
            ]
            for kw in keyword_pool:
                if len(links) >= max_links:
                    break
                needed = max_links - len(links)
                extra = search_companies(kw, needed, max_pages=5)
                for url in extra:
                    if url not in links:
                        links.append(url)
                    if len(links) >= max_links:
                        break

        print(f"  ✅ Đã tìm thấy {len(links)} link công ty")
        return links
        
    except Exception as e:
        print(f"  ❌ Lỗi: {str(e)}")
        return []

def search_companies_by_location(province, max_results=10):
    """Tìm kiếm công ty theo tỉnh/thành phố để lấy thêm link."""
    print(f"  🔍 Tìm kiếm công ty ở {province}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        links = []
        search_url = f"https://thongtincongty.vn/?s={province}"
        resp = requests.get(search_url, headers=headers, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/ma-so-thue/' in href or '/cong-ty/' in href:
                    full_url = href if href.startswith('http') else f"https://thongtincongty.vn{href}"
                    if full_url not in links:
                        links.append(full_url)
                    if len(links) >= max_results:
                        break
        time.sleep(0.1)
        return links
    except Exception as e:
        return []

def search_companies(keyword, max_results=10, max_pages=5):
    """Tìm kiếm công ty theo từ khóa, hỗ trợ phân trang."""
    print(f"\n🔍 Tìm kiếm công ty với từ khóa: '{keyword}'...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        links = []

        for page in range(1, max_pages + 1):
            search_url = f"https://thongtincongty.vn/?s={keyword}" if page == 1 else f"https://thongtincongty.vn/page/{page}/?s={keyword}"
            resp = requests.get(search_url, headers=headers, timeout=30)

            # Trang /page/2/ của tìm kiếm hiện trả về 404, dừng phân trang nếu gặp
            if resp.status_code == 404 and page > 1:
                print(f"  ⚠️ Trang {search_url} trả về 404, dừng phân trang tìm kiếm.")
                break

            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/ma-so-thue/' in href or '/cong-ty/' in href:
                    full_url = href if href.startswith('http') else f"https://thongtincongty.vn{href}"
                    if full_url not in links:
                        links.append(full_url)
                    if len(links) >= max_results:
                        break
            if len(links) >= max_results:
                break
            time.sleep(0.1)
        
        print(f"  ✅ Đã tìm thấy {len(links)} công ty")
        return links
        
    except Exception as e:
        print(f"  ❌ Lỗi tìm kiếm: {str(e)}")
        return []

def search_by_industry(industry, max_results=10):
    """Tìm kiếm theo ngành nghề cụ thể"""
    print(f"  🏭 Tìm kiếm theo ngành: {industry}...")
    return search_companies(industry, max_results, max_pages=3)

def search_by_business_type(biz_type, max_results=10):
    """Tìm kiếm theo loại hình doanh nghiệp"""
    print(f"  🏢 Tìm kiếm loại hình: {biz_type}...")
    return search_companies(biz_type, max_results, max_pages=3)

def deduplicate_urls(urls):
    """Loại bỏ URLs trùng lặp, giữ thứ tự"""
    seen = set()
    unique = []
    for url in urls:
        url_clean = url.strip().lower()
        if url_clean not in seen:
            seen.add(url_clean)
            unique.append(url)
    return unique
    info = {
        "url": url,
        "crawled_at": datetime.now().isoformat(),
        "company_legal_info": {},
        "company_description": "",
        "reviews": []
    }
    
    # Tìm bảng thông tin (table)
    table = soup.find('table')
    if not table:
        return info
    
    # Parse từng dòng trong bảng
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 2:
            label = norm_text(cells[0].get_text())
            value = norm_text(cells[1].get_text())
            
            # Mapping các trường
            if 'Tên đơn vị' in label or 'Tên doanh nghiệp' in label:
                info["company_name"] = value
            elif 'Mã số thuế' in label and 'cũ' not in label.lower():
                info["company_legal_info"]["ma_so_thue"] = value
            elif 'Mã số thuế cũ' in label:
                info["company_legal_info"]["ma_so_thue_cu"] = value
            elif 'Địa chỉ' in label:
                info["company_legal_info"]["dia_chi"] = value
            elif 'Trạng thái' in label:
                info["company_legal_info"]["trang_thai"] = value
            elif 'Cơ quan thuế' in label:
                info["company_legal_info"]["co_quan_thue"] = value
            elif 'PP tính thuế' in label or 'Phương pháp' in label:
                info["company_legal_info"]["phuong_phap_tinh_thue"] = value
            elif 'Ngành nghề' in label:
                info["company_legal_info"]["nganh_nghe"] = value
            elif 'Chương' in label or 'Khoản' in label:
                info["company_legal_info"]["chuong_khoan"] = value
    
    return info

def crawl_requests(url):
    """Crawl dữ liệu bằng requests (KHÔNG CẦN MỞ TRÌNH DUYỆT - NHANH)"""
    print(f"\n📍 Crawl: {url}")
    
    try:
        # Giả lập trình duyệt bằng headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        # Gửi request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse thông tin công ty
        data = parse_company_info(response.text, url)
        
        # Parse reviews
        print("  - Parsing review/bình luận...")
        data["reviews"] = parse_reviews(response.text)
        
        print(f"  ✅ Công ty: {data.get('company_name', 'N/A')}")
        print(f"  ✅ Thông tin pháp lý: {len(data.get('company_legal_info', {}))} field")
        print(f"  ✅ Review: {len(data.get('reviews', []))} bình luận")
        print(f"  ✅ Giới thiệu công ty: {len(data.get('company_description', ''))} ký tự")
        
        return data
        
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return None

def find_chrome_binary():
    """Tìm Chrome binary ở các vị trí phổ biến"""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def crawl_selenium():
    """Crawl dữ liệu công ty sử dụng Selenium"""
    print("=" * 70)
    print("🌐 CRAWL DỮ LIỆU TỪ TOPCV")
    print("=" * 70)
    
    print(f"\n📍 URL: {COMPANY_URL}")
    
    driver = None
    try:
        # Thử tìm Chrome trước
        chrome_binary = find_chrome_binary()
        
        if chrome_binary:
            print("⏳ Khởi động trình duyệt Chrome...")
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = chrome_binary
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            # chrome_options.add_argument("--headless")  # Chạy ẩn (uncomment nếu muốn)
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Nếu không có Chrome, dùng Edge
            print("⚠️ Không tìm thấy Chrome. Chuyển sang sử dụng Edge...")
            print("⏳ Khởi động trình duyệt Edge...")
            edge_options = webdriver.EdgeOptions()
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            # edge_options.add_argument("--headless")  # Chạy ẩn (uncomment nếu muốn)
            
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=edge_options)
        
        # Truy cập trang
        print("⏳ Đang tải trang...")
        driver.get(COMPANY_URL)
        
        # Chờ trang load
        wait = WebDriverWait(driver, 10)
        print("⏳ Chờ trang render...")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "company-info")))
        
        # Scroll để load thêm dữ liệu
        print("⏳ Scroll trang để load dữ liệu...")
        for i in range(3):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
        
        # Lấy HTML sau khi render
        html = driver.page_source
        
        print("✅ Trang đã load. Đang parse dữ liệu...")
        
        # Parse thông tin công ty
        data = parse_company_info(html, COMPANY_URL)
        
        # Parse reviews
        print("  - Parsing review/bình luận...")
        data["reviews"] = parse_reviews(html)
        
        print(f"  ✅ Công ty: {data.get('company_name', 'N/A')}")
        print(f"  ✅ Thông tin pháp lý: {len(data.get('company_legal_info', {}))} field")
        print(f"  ✅ Review: {len(data.get('reviews', []))} bình luận")
        print(f"  ✅ Giới thiệu công ty: {len(data.get('company_description', ''))} ký tự")
        
        return data
        
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return None
    
    finally:
        if driver:
            driver.quit()
            print("✅ Đã đóng trình duyệt")

def save_data(data: dict, filename: str = "companies_data.csv", is_first: bool = False) -> None:
    """Lưu dữ liệu vào file CSV (mỗi hàng = 1 công ty).

    - Bỏ qua nếu trùng mã số thuế (ma_so_thue).
    - Có retry nếu file đang bị khóa (PermissionError).
    """
    if not data:
        print("❌ Không có dữ liệu để lưu")
        return

    # Lưu vào thư mục dự án
    try:
        data_dir = Path("D:\\UnderFitting_SEG301\\crawled_data")
        if not data_dir.exists():
            data_dir.mkdir(exist_ok=True)
        filepath = data_dir / filename
    except Exception as e:
        print(f"⚠️ Không thể lưu vào D:\\UnderFitting_SEG301\\crawled_data ({e}), lưu file vào thư mục hiện tại")
        filepath = Path(filename)

    FIXED_FIELDNAMES = [
        'Tên công ty',
        'Mã số thuế',
        'Mã số thuế cũ',
        'Địa chỉ',
        'Trạng thái',
        'Cơ quan thuế',
        'Phương pháp tính thuế',
        'Ngành nghề',
        'Chương-khoản',
        'URL',
        'Thời gian crawl'
    ]

    company_name = data.get('company_name', '')
    url = data.get('url', '')
    crawled_at = data.get('crawled_at', '')
    legal_info = data.get('company_legal_info', {})

    row_data = {
        'Tên công ty': company_name,
        'Mã số thuế': legal_info.get('ma_so_thue', ''),
        'Mã số thuế cũ': legal_info.get('ma_so_thue_cu', ''),
        'Địa chỉ': legal_info.get('dia_chi', ''),
        'Trạng thái': legal_info.get('trang_thai', ''),
        'Cơ quan thuế': legal_info.get('co_quan_thue', ''),
        'Phương pháp tính thuế': legal_info.get('phuong_phap_tinh_thue', ''),
        'Ngành nghề': legal_info.get('nganh_nghe', ''),
        'Chương-khoản': legal_info.get('chuong_khoan', ''),
        'URL': url,
        'Thời gian crawl': crawled_at
    }

    new_mst = (row_data.get('Mã số thuế') or '').strip()

    if filepath.exists() and not is_first and new_mst:
        try:
            with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                existing_mst = {(row.get('Mã số thuế') or '').strip() for row in reader}
            if new_mst in existing_mst:
                print(f"  ⚠️ Bỏ qua (trùng mã số thuế): {new_mst}")
                return
        except Exception as e:
            print(f"  ⚠️ Không đọc được file để kiểm tra trùng: {e}")

    file_exists = filepath.exists()
    mode = 'w' if (is_first and not file_exists) else 'a'
    write_header = (is_first and not file_exists) or not file_exists

    max_retries = 20
    for attempt in range(max_retries):
        try:
            with open(filepath, mode, encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=FIXED_FIELDNAMES)

                if write_header:
                    writer.writeheader()

                writer.writerow(row_data)

            # Append seen URL/MST
            if url:
                append_seen_line(SEEN_URLS_PATH, url.strip().lower())
            if new_mst:
                append_seen_line(SEEN_MST_PATH, new_mst)

            print(f"  ✅ Đã lưu vào: {filepath}")
            return

        except PermissionError:
            if attempt < max_retries - 1:
                print(f"  ⚠️ File đang được mở, thử lại... ({attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            else:
                print(f"  ❌ Không thể ghi sau {max_retries} lần thử. Vui lòng đóng Excel và chạy lại!")
                return

        except Exception as e:
            print(f"  ❌ Lỗi khi lưu: {str(e)}")
            return

async def fetch_one_async(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore, retries: int = 2) -> Optional[dict]:
    """Fetch một URL bất đồng bộ với retry"""
    async with semaphore:
        for attempt in range(retries + 1):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status in (403, 429):
                        await asyncio.sleep(1 + attempt)
                        continue
                    resp.raise_for_status()
                    html = await resp.text()
                    data = parse_company_info(html, url)
                    return data
            except Exception:
                if attempt < retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
        return None

async def crawl_concurrent(urls: List[str], max_concurrency: int = 10) -> List[dict]:
    """Crawl nhiều URL đồng thời với giới hạn kết nối"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
    }
    sem = asyncio.Semaphore(max_concurrency)
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [fetch_one_async(session, url, sem) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]

if __name__ == "__main__":
    print("=" * 70)
    print("🌐 CRAWL NHANH DỮ LIỆU CÔNG TY")
    print("=" * 70)
    
    print("\nChọn cách tìm kiếm công ty:")
    print("  1. Tìm kiếm theo từ khóa")
    print("  2. Tìm kiếm ĐA DẠNG (khuyến nghị - ít trùng nhất)")
    
    choice = input("\nNhập lựa chọn (1/2, mặc định 2): ").strip() or "2"
    
    urls = []
    
    if choice == "1":
        # Tìm kiếm theo từ khóa
        keyword = input("Nhập từ khóa tìm kiếm: ").strip()
        max_results = input("Số lượng (mặc định 100): ").strip()
        max_results = int(max_results) if max_results.isdigit() else 100
        urls = search_companies(keyword, max_results, max_pages=20)
    
    else:  # choice == "2" - diverse search
        # Tìm kiếm ĐA DẠNG: tỉnh + ngành + loại hình (ít trùng nhất)
        max_companies = input("Nhập số lượng công ty cần lấy (mặc định 200): ").strip()
        max_companies = int(max_companies) if max_companies.isdigit() else 200
        
        print("\n🎯 Chế độ ĐA DẠNG: tỉnh + ngành nghề + loại hình DN...")
        urls = []
        
        # 1. Tìm theo các tỉnh đa dạng (chọn lọc)
        provinces = ["Hà Nội", "TP.HCM", "Đà Nẵng", "Hải Phòng", "Cần Thơ", 
                     "Bình Dương", "Đồng Nai", "Nghệ An", "Thanh Hóa", "Quảng Ninh",
                     "Khánh Hòa", "Lâm Đồng", "Bà Rịa Vũng Tàu", "Long An", "Tiền Giang"]
        
        per_source = max(5, max_companies // 60)  # Chia đều cho ~60 nguồn
        
        for prov in provinces:
            if len(urls) >= max_companies:
                break
            extra = search_companies_by_location(prov, max_results=per_source)
            urls.extend(extra)
        
        # 2. Tìm theo ngành nghề đa dạng
        industries = [
            "xây dựng", "bất động sản", "công nghệ thông tin", "thương mại điện tử",
            "sản xuất", "chế biến thực phẩm", "dệt may", "da giày", "điện tử",
            "logistics", "vận tải", "du lịch", "khách sạn", "nhà hàng",
            "y tế", "dược phẩm", "giáo dục", "đào tạo", "tư vấn",
            "marketing", "quảng cáo", "thiết kế", "in ấn", "xuất bản",
            "nông nghiệp", "thủy sản", "chăn nuôi", "lâm nghiệp",
            "năng lượng", "điện lực", "xăng dầu", "hóa chất",
            "ngân hàng", "bảo hiểm", "chứng khoán", "tài chính",
            "bưu chính viễn thông", "truyền thông", "giải trí"
        ]
        
        for ind in industries:
            if len(urls) >= max_companies:
                break
            extra = search_by_industry(ind, max_results=per_source)
            urls.extend(extra)
        
        # 3. Tìm theo loại hình doanh nghiệp
        business_types = [
            "TNHH một thành viên", "TNHH hai thành viên", 
            "công ty cổ phần", "công ty TNHH",
            "doanh nghiệp tư nhân", "hộ kinh doanh",
            "hợp tác xã", "chi nhánh", "văn phòng đại diện"
        ]
        
        for btype in business_types:
            if len(urls) >= max_companies:
                break
            extra = search_by_business_type(btype, max_results=per_source)
            urls.extend(extra)
        
        # 4. Deduplicate URLs
        print(f"\n🔄 Đang loại bỏ URL trùng lặp...")
        print(f"  Trước: {len(urls)} URLs")
        urls = deduplicate_urls(urls)
        print(f"  Sau: {len(urls)} URLs (đã loại {len(set([u.lower() for u in urls])) - len(urls)} trùng)")
        
        # Giới hạn số lượng nếu vượt quá
        if len(urls) > max_companies:
            urls = urls[:max_companies]
            print(f"  ✂️ Cắt xuống còn {max_companies} URLs")
        
        # Deduplicate URLs đã được thực hiện ở trên rồi
    
    # Deduplicate URLs cho mode 1 (keyword search)
    if choice == "1":
        original_count = len(urls)
        urls = deduplicate_urls(urls)
        if len(urls) < original_count:
            print(f"\n🔄 Đã loại {original_count - len(urls)} URL trùng lặp ({len(urls)} còn lại)")
    
    if not urls:
        print("❌ Không có URL nào để crawl!")
    else:
        output_file = "all_companies_data.csv"

        # Filter out already-seen URLs
        seen_urls = load_seen_set(SEEN_URLS_PATH)
        before = len(urls)
        urls = [u for u in urls if u.strip().lower() not in seen_urls]
        after = len(urls)
        if after < before:
            print(f"\n🔁 Bỏ qua URL đã crawl: {before - after} (còn {after})")

        # Optional min year filter
        min_year_input = input("Bỏ dữ liệu cũ trước năm (nhập để bỏ qua): ").strip()
        min_year = int(min_year_input) if min_year_input.isdigit() else None

        print(f"\n📊 Tổng số công ty: {len(urls)}")
        print(f"📁 File: D:\\UnderFitting_SEG301\\crawled_data\\{output_file}")

        concurrency = input("\nSố kết nối song song (mặc định 15): ").strip()
        concurrency = int(concurrency) if concurrency.isdigit() else 15
        print(f"\n🚀 Bắt đầu crawl với {concurrency} kết nối song song...\n")
        
        start_time = time.time()
        results = asyncio.run(crawl_concurrent(urls, max_concurrency=concurrency))
        elapsed = time.time() - start_time

        print(f"\n✅ Crawl: {len(results)}/{len(urls)} công ty trong {elapsed:.2f}s")
        print("\n💾 Lưu dữ liệu...")

        success_count = 0
        for idx, data in enumerate(results, 1):
            if not data or not data.get('company_name'):
                continue

            # Skip old records if requested
            if min_year is not None:
                yr = extract_year_from_legal_info(data.get('company_legal_info', {}))
                if yr is not None and yr < min_year:
                    continue

            save_data(data, output_file, is_first=(idx == 1))
            success_count += 1
            if idx % 50 == 0:
                print(f"  [{idx}/{len(results)}] Đang lưu...")

        fail_count = len(urls) - success_count
        
        print("\n" + "=" * 70)
        print("✨ HOÀN THÀNH!")
        print(f"  ✅ Thành công: {success_count}/{len(urls)} công ty")
        print(f"  ❌ Bỏ qua/không lưu: {fail_count}/{len(urls)} công ty")
        print(f"  📁 File: D:\\UnderFitting_SEG301\\crawled_data\\{output_file}")
        print("=" * 70)