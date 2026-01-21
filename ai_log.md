# AI INTERACTION LOG – MERGED VERSION

**Project:** Hệ thống Crawl & Chuẩn hoá dữ liệu doanh nghiệp Việt Nam  
**Mục tiêu:** BizInfo & Review 360  
**Thời gian:** 2026-01-08 → 2026-01-21  

---

## Date: 2026-01-08

### Task: Khảo sát nguồn dữ liệu và thiết kế kiến trúc hệ thống crawl doanh nghiệp

**User (Cả nhóm):**  
Tôi cần các website có thể crawl dữ liệu doanh nghiệp phục vụ BizInfo & Review 360, gồm thông tin pháp lý (nguồn sạch) và review/bình luận (nguồn bẩn). Thách thức là merge dữ liệu theo tên công ty hoặc mã số thuế.

**AI (ChatGPT):**  
Đề xuất các nguồn dữ liệu phổ biến tại Việt Nam (infodoanhnghiep.com, hsctvn.com, thongtincongty.vn, careerlink.vn, masothue.vn…). Phân loại nguồn sạch/nguồn bẩn và phân tích kiến trúc crawler 2 tầng (list → detail), cùng các rủi ro khi merge dữ liệu theo tên doanh nghiệp hoặc MST.

---

## Date: 2026-01-08

### Task: Triển khai crawler list–detail cho infodoanhnghiep.com

**User (Hậu):**  
Viết code crawl dữ liệu doanh nghiệp, lưu CSV, có log tiến trình và hỗ trợ resume.

**AI (ChatGPT):**  
Cung cấp skeleton crawler Python (requests + BeautifulSoup), hỗ trợ resume bằng START_ROW, log theo PAGE | ROW, thiết kế schema CSV cho dữ liệu doanh nghiệp.

---

## Date: 2026-01-08

### Task: Debug lỗi crawler không ghi dữ liệu CSV

**User (Hậu):**  
Code chạy nhưng file CSV trống, danh sách công ty không lấy được.

**AI (ChatGPT):**  
Phân tích nguyên nhân do selector HTML không khớp DOM thực tế. Hướng dẫn inspect HTML và điều chỉnh selector để lấy đúng link công ty.

---

## Date: 2026-01-08

### Task: Crawl trang chi tiết và giới hạn phạm vi crawl

**User (Hậu):**  
Tôi chỉ muốn crawl nội dung trang chi tiết, không theo các link con.

**AI (ChatGPT):**  
Viết hàm crawl trang chi tiết chỉ parse khối nội dung chính, trích xuất các trường: tên doanh nghiệp, mã số thuế, địa chỉ, người đại diện, ngày cấp giấy phép, tình trạng hoạt động.

---

## Date: 2026-01-08

### Task: Xử lý timeout và mất dữ liệu khi ghi CSV

**User (Hậu):**  
Một số trang bị timeout, có trang log được tên nhưng khi ghi CSV thì bị mất.

**AI (ChatGPT):**  
Chỉ ra nguyên nhân do thiếu timeout/retry và logic lấy tên công ty không ổn định. Đề xuất thêm retry, timeout và lấy dữ liệu trực tiếp từ DOM.

---

## Date: 2026-01-09  
### (Luồng song song – Duy)

### Task: Crawl dữ liệu doanh nghiệp từ thongtincongty.vn

**User (Duy):**  
Khi crawl tự động chỉ lấy được khoảng 20 công ty, tôi muốn crawl được nhiều hơn.

**AI (ChatGPT):**  
Phát hiện website không hỗ trợ phân trang (page > 1 trả 404). Đề xuất dừng phân trang sớm và mở rộng dữ liệu bằng chiến lược crawl theo nhiều keyword.

---

## Date: 2026-01-09  
### (Luồng song song – Duy)

### Task: Khắc phục lỗi ghi đè dữ liệu CSV

**User (Duy):**  
Mỗi lần crawl thì dữ liệu cũ bị mất.

**AI (ChatGPT):**  
Xác định nguyên nhân do luôn mở file ở chế độ write. Đề xuất kiểm tra file tồn tại và chuyển sang append mode, chỉ ghi header khi file chưa tồn tại.

---

## Date: 2026-01-09  
### (Luồng song song – Huy)

### Task: Nghiên cứu và crawl dữ liệu doanh nghiệp từ CareerLink.vn

**User (Huy):**  
Tạo code scrape thông tin công ty từ careerlink.vn.

**AI (ChatGPT):**  
Phân tích kiến trúc CareerLink (class CSS dùng chung, render động). Viết script Python scrape danh sách công ty, giả lập User-Agent và thêm delay để tránh bị chặn.

---

## Date: 2026-01-09  
### (Luồng song song – Huy)

### Task: Debug lỗi trích xuất sai dữ liệu trên CareerLink

**User (Huy):**  
Cột Salary bị dính chữ “Lưu”, cột Company lấy nhầm địa điểm.

**AI (ChatGPT):**  
Xác định nguyên nhân do selector CSS không phân biệt rõ thẻ. Điều chỉnh selector, loại bỏ text rác, ưu tiên class định danh đúng và bổ sung cột URL chi tiết.

---

## Date: 2026-01-10

### Task: Mở rộng crawler bất đồng bộ (hsctvn.com)

**User (Hậu):**  
Viết crawler async, có phân trang, resume và tránh bị chặn.

**AI (ChatGPT):**  
Thiết kế crawler async với aiohttp + asyncio, dùng semaphore giới hạn concurrent requests, bổ sung retry, delay ngẫu nhiên và log HTTP status.

---

## Date: 2026-01-10

### Task: Bổ sung retry, log HTTP status và tránh bị chặn

**User (Hậu):**  
Thêm retry khi timeout và in HTTP status code.

**AI (ChatGPT):**  
Bổ sung retry có kiểm soát, không retry 404, thêm backoff nhẹ và in log HTTP status cho từng request.

---

## Date: 2026-01-11

### Task: Tối ưu hiệu năng crawler

**User (Hậu & Duy):**  
Crawler chạy chậm, cần tối ưu.

**AI (ChatGPT):**  
Phân tích điểm nghẽn (sleep nhiều, ghi file từng dòng). Đề xuất tái sử dụng HTTP session, điều chỉnh delay và ghi CSV theo batch.

---

## Date: 2026-01-11

### Task: Mở rộng quy mô crawl trên thongtincongty.vn

**User (Duy):**  
Mỗi lần crawl chỉ được ~20 công ty, cần tăng số lượng.

**AI (ChatGPT):**  
Đề xuất chiến lược multi-keyword, search theo tỉnh/thành, kết hợp nhiều nguồn để đạt 150+ công ty mỗi lần crawl.

---

## Date: 2026-01-12

### Task: Làm sạch và chuẩn hoá dữ liệu CSV

**User (Cả nhóm):**  
Dữ liệu crawl có HTML rác, lệch cột, ngày không thống nhất.

**AI (ChatGPT):**  
Xây dựng pipeline ETL chuẩn: clean text, chuẩn hoá tên doanh nghiệp, chuẩn hoá ngày bằng regex linh hoạt, giữ nguyên schema CSV.

---

## Date: 2026-01-12

### Task: Tích hợp logic clean trực tiếp vào crawler

**User (Hậu):**  
Tôi muốn dữ liệu crawl ra đã sạch ngay từ đầu.

**AI (ChatGPT):**  
Chỉnh sửa crawler để tích hợp logic clean ngay trong bước parse HTML, đảm bảo dữ liệu đầu ra thống nhất và ổn định.

---

## Date: 2026-01-16

### Task: Phát hiện và loại bỏ dữ liệu trùng lặp

**User (Cả nhóm):**  
Sau khi crawl xong, dữ liệu CSV bị trùng nhiều dòng.

**AI (ChatGPT):**  
Xây dựng logic detect duplicate dựa trên tên doanh nghiệp – mã số thuế – địa chỉ, giữ bản ghi hợp lệ đầu tiên và ghi đè lại file CSV gốc mà không thay đổi schema.

---

## Date: 2026-01-21

### Task: Chuyển file csv sang JSON

**User (Cả nhóm):**  
Tôi muốn chuyển file csv sang định dạng JSON

**AI (ChatGPT):**  
Viết code để chuyển đổi từ file csv sang JSON, mỗi dòng là một object, ghi lại thành file mới.


## END OF AI INTERACTION LOG
