import requests
from bs4 import BeautifulSoup
import csv
import time
import random

# Cấu hình Header giả lập trình duyệt và Referer để tránh bị hệ thống chặn [1, 2]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.careerlink.vn/"
}

BASE_URL = "https://www.careerlink.vn"
# Link tìm kiếm tại An Giang
TARGET_URL = "https://www.careerlink.vn/vieclam/list"

def scrape_jobs(max_pages=2):
    job_list = []
    
    for page in range(1, max_pages + 1):
        # CareerLink sử dụng tham số?page=N để điều hướng [3]
        url = f"{TARGET_URL}?page={page}"
        print(f"--- Đang quét dữ liệu trang {page}/{max_pages} ---")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code!= 200:
                print(f"Lỗi truy cập trang {page}. Dừng lại.")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Lấy danh sách các khối công việc dựa trên cấu trúc thẻ job-item [4, 5]
            items = soup.select(".job-item,.media.job-item") 
            
            if not items:
                print("Không tìm thấy thêm công việc.")
                break

            for item in items:
                try:
                    # 1. TIÊU ĐỀ VÀ URL CÔNG VIỆC
                    # Trích xuất đường dẫn tương đối và nối với BASE_URL [2, 6]
                    title_tag = item.select_one("a.job-link, h3.job-title a")
                    title = title_tag.get_text(strip=True) if title_tag else "N/A"
                    job_url = BASE_URL + title_tag['href'] if title_tag and title_tag.has_attr('href') else "N/A"
                    
                    # 2. TÊN CÔNG TY (Sử dụng selector.job-company chính xác từ mã nguồn bạn cung cấp) 
                    company_tag = item.select_one(".job-company")
                    company = company_tag.get_text(strip=True) if company_tag else "N/A"
                    
                    # 3. ĐỊA ĐIỂM
                    location_tag = item.select_one(".job-location")
                    location = location_tag.get_text(strip=True) if location_tag else "Bắc Kạn"
                    
                    # 4. MỨC LƯƠNG (Loại bỏ nút "Lưu" và tách cấp bậc) 
                    salary = "Thương lượng"
                    level = "N/A"
                    potential_salaries = item.select(".text-primary,.job-salary")
                    for tag in potential_salaries:
                        text = tag.get_text(strip=True)
                        # Kiểm tra nội dung văn bản để tránh lấy nhầm nút "Lưu"
                        if text and text!= "Lưu":
                            if "|" in text:
                                parts = [p.strip() for p in text.split("|")]
                                salary = parts
                                level = parts[8] if len(parts) > 1 else "N/A"
                            else:
                                salary = text
                            break

                    # 5. THỜI GIAN CẬP NHẬT
                    update_tag = item.select_one(".job-updated-at,.text-muted")
                    updated_at = update_tag.get_text(strip=True) if update_tag else "N/A"

                    # Thêm dữ liệu vào danh sách với đầy đủ 7 cột
                    job_list.append({
                        "Job Title": title,
                        "Company": company,
                        "Location": location,
                        "Salary": salary,
                        "Level": level,
                        "Updated": updated_at,
                        "URL": job_url # Cột URL theo yêu cầu của bạn 
                    })
                except Exception:
                    continue

            # Nghỉ ngẫu nhiên để tránh bị hệ thống chặn IP 
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            print(f"Lỗi kết nối: {e}")
            break

    # Lưu kết quả vào file CSV
    if job_list:
        # Định nghĩa thứ tự các cột để khớp với hình ảnh Excel của bạn
        fieldnames = ["Job Title", "Company", "Location", "Salary", "Level", "Updated", "URL"]
        filename = "careerlink_List_with_urls.csv"
        
        # Sử dụng utf-8-sig để Excel hiển thị đúng tiếng Việt có dấu
        with open(filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(job_list)
        print(f"Thành công! Đã lưu {len(job_list)} công việc vào '{filename}'")
    else:
        print("Không có dữ liệu để lưu.")

if __name__ == "__main__":
    scrape_jobs(max_pages=715)
