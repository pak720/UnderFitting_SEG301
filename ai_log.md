# AI INTERACTION LOG – MERGED VERSION

**Project:** Hệ thống Crawl & Chuẩn hoá dữ liệu doanh nghiệp Việt Nam  
**Mục tiêu:** BizInfo & Review 360  
**Thời gian:** 2026-01-08 → 2026-01-21  

---

## Thành viên 1: Huy
##AI INTERACTION LOG

Date: 2026-01-09
Task: Nghiên cứu cấu trúc kỹ thuật và lập kế hoạch trích xuất dữ liệu CareerLink.vn

User: tạo một cái code để scrape các thông tin về công ty của http://careerlink.vn/

AI (Assistant): Đã thực hiện phân tích kiến trúc hệ thống của CareerLink, xác định các rào cản như tệp robots.txt không hợp lệ, cơ chế render phía client và các yêu cầu về token để truy cập dữ liệu lương. Cung cấp báo cáo chi tiết về danh sách 108 nhà tuyển dụng hàng đầu và các lĩnh vực kinh doanh trọng điểm như CNTT, Kế toán và Xây dựng.

Date: 2026-01-09
Task: Viết mã nguồn Python Scraper cơ bản

User: generate một python code hoàn chỉnh cho tôi

AI (Assistant): Xây dựng đoạn mã Python sử dụng thư viện requests và BeautifulSoup. Mã nguồn tập trung vào việc lấy danh sách tên công ty, quy mô và mô tả từ trang "Nhà tuyển dụng hàng đầu", tích hợp cơ chế giả lập trình duyệt (User-Agent) và thời gian nghỉ ngẫu nhiên để tránh bị chặn IP.

Date: 2026-01-09
Task: Tùy chỉnh mã nguồn cho kết quả tìm kiếm khu vực TP.HCM

User: Tôi muốn scrape link này https://www.careerlink.vn/tim-viec-lam-tai/ho-chi-minh/HCM

AI (Assistant): Điều chỉnh script để xử lý cấu trúc của trang kết quả tìm kiếm. Tích hợp cơ chế phân trang tự động bằng tham số ?page=N và sử dụng dictionary để lọc bỏ các doanh nghiệp đăng nhiều tin tuyển dụng trùng lặp trong danh sách.

Date: 2026-01-09
Task: Debug lỗi trích xuất cột Lương (Salary) bị dính chữ "Lưu"

User: bạn có thể chỉnh lại code được không cái cột salary tai sao nó lại lưu là "lưu" hãy chỉnh lại sao cho nó scrape đúng nhé

AI (Assistant): Xác định nguyên nhân do thẻ nút "Lưu việc làm" có cùng class CSS màu xanh (text-primary) với phần hiển thị lương. Đã cập nhật logic kiểm tra: if text!= "Lưu" để bỏ qua các thẻ rác và lấy đúng thông tin mức lương thực tế.

Date: 2026-01-09
Task: Sửa lỗi cột Công ty bị lấy nhầm thành địa điểm (Bắc Kạn)

User: tôi muốn bạn sửa code, cái cột company phải lưu tên công ty như trong hình tôi đánh dấu đỏ, sao lại là Bắc Kạn

AI (Assistant): Phân tích và nhận thấy các thẻ địa điểm sử dụng class chung khiến bộ chọn bị nhầm lẫn. Đã tối ưu hóa lại selector, ưu tiên class định danh .company-name và bổ sung logic tách biệt hoàn toàn giữa cột doanh nghiệp và cột địa điểm.

Date: 2026-01-09
Task: Tối ưu hóa bộ chọn dựa trên Inspect Element và bổ sung URL

User: vẫn sai, đây là cái script tham khảo [Ảnh Inspect Element], Tốt, sửa lại cái python code, sao cho nó lưu kèm theo cột Url từng công ty nhé

AI (Assistant): Sử dụng chính xác class .job-company trích xuất từ hình ảnh Inspect Element của người dùng cung cấp để lấy tên công ty chính xác tuyệt đối. Đồng thời, cập nhật mã nguồn để trích xuất thuộc tính href, nối với BASE_URL nhằm cung cấp đường dẫn chi tiết cho từng công việc trong file CSV.

## END OF AI INTERACTION LOG
