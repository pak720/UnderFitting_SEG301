# AI INTERACTION LOG – MERGED VERSION

**Project:** Hệ thống Crawl & Chuẩn hoá dữ liệu doanh nghiệp Việt Nam  
**Mục tiêu:** BizInfo & Review 360  
**Thời gian:** 2026-01-08 → 2026-01-21  

---

## Thành viên 1: Huy

### Date: 2026-01-09
**Task:** Nghiên cứu cấu trúc kỹ thuật và lập kế hoạch trích xuất dữ liệu CareerLink.vn

**User:** tạo một cái code để scrape các thông tin về công ty của http://careerlink.vn/

**AI (Gemini):** Đã thực hiện phân tích kiến trúc hệ thống của CareerLink, xác định các rào cản như tệp robots.txt không hợp lệ, cơ chế render phía client và các yêu cầu về token để truy cập dữ liệu lương. Cung cấp báo cáo chi tiết về danh sách 108 nhà tuyển dụng hàng đầu và các lĩnh vực kinh doanh trọng điểm như CNTT, Kế toán và Xây dựng.

---

#### Date: 2026-01-09
**Task:** Viết mã nguồn Python Scraper cơ bản

**User:** generate một python code hoàn chỉnh cho tôi

**AI (Gemini):** Xây dựng đoạn mã Python sử dụng thư viện requests và BeautifulSoup. Mã nguồn tập trung vào việc lấy danh sách tên công ty, quy mô và mô tả từ trang "Nhà tuyển dụng hàng đầu", tích hợp cơ chế giả lập trình duyệt (User-Agent) và thời gian nghỉ ngẫu nhiên để tránh bị chặn IP.

---

### Date: 2026-01-09
**Task:** Tùy chỉnh mã nguồn cho kết quả tìm kiếm khu vực TP.HCM

**User:** Tôi muốn scrape link này https://www.careerlink.vn/tim-viec-lam-tai/ho-chi-minh/HCM

**AI (Gemini):** Điều chỉnh script để xử lý cấu trúc của trang kết quả tìm kiếm. Tích hợp cơ chế phân trang tự động bằng tham số ?page=N và sử dụng dictionary để lọc bỏ các doanh nghiệp đăng nhiều tin tuyển dụng trùng lặp trong danh sách.

---

### Date: 2026-01-09
**Task:** Debug lỗi trích xuất cột Lương (Salary) bị dính chữ "Lưu"

**User:** bạn có thể chỉnh lại code được không cái cột salary tai sao nó lại lưu là "lưu" hãy chỉnh lại sao cho nó scrape đúng nhé

**AI (Gemini):** Xác định nguyên nhân do thẻ nút "Lưu việc làm" có cùng class CSS màu xanh (text-primary) với phần hiển thị lương. Đã cập nhật logic kiểm tra: if text!= "Lưu" để bỏ qua các thẻ rác và lấy đúng thông tin mức lương thực tế.

---

### Date: 2026-01-09
**Task:** Sửa lỗi cột Công ty bị lấy nhầm thành địa điểm (Bắc Kạn)

**User:** tôi muốn bạn sửa code, cái cột company phải lưu tên công ty như trong hình tôi đánh dấu đỏ, sao lại là Bắc Kạn

**AI (Gemini):** Phân tích và nhận thấy các thẻ địa điểm sử dụng class chung khiến bộ chọn bị nhầm lẫn. Đã tối ưu hóa lại selector, ưu tiên class định danh .company-name và bổ sung logic tách biệt hoàn toàn giữa cột doanh nghiệp và cột địa điểm.

---

### Date: 2026-01-09
**Task:** Tối ưu hóa bộ chọn dựa trên Inspect Element và bổ sung URL

**User:** vẫn sai, đây là cái script tham khảo [Ảnh Inspect Element], Tốt, sửa lại cái python code, sao cho nó lưu kèm theo cột Url từng công ty nhé

**AI (Gemini):** Sử dụng chính xác class .job-company trích xuất từ hình ảnh Inspect Element của người dùng cung cấp để lấy tên công ty chính xác tuyệt đối. Đồng thời, cập nhật mã nguồn để trích xuất thuộc tính href, nối với BASE_URL nhằm cung cấp đường dẫn chi tiết cho từng công việc trong file CSV.

---
# AI Log – JSONL & JSON Fuzzy Matching Debug

## Date
2026-01-23

## Task
So sánh và hợp nhất (merge) dữ liệu doanh nghiệp giữa:
- **File JSONL** (nguồn dữ liệu đăng ký doanh nghiệp – có trường `Tên doanh nghiệp`)
- **File JSON** (nguồn đánh giá doanh nghiệp – có trường `company_name`)

Mục tiêu là fuzzy match tên doanh nghiệp giữa hai nguồn và **chỉ merge khi thực sự cùng một doanh nghiệp**, đồng thời **phát hiện và sửa lỗi match sai nghiêm trọng (false positive)**.


## Background

Người dùng đang xử lý tập dữ liệu doanh nghiệp lớn, trong đó:
- File JSONL chứa thông tin pháp lý (MST, địa chỉ, tình trạng hoạt động, …)
- File JSON chứa thông tin đánh giá, URL, rating, review

Yêu cầu:
- So sánh tên doanh nghiệp giữa hai file
- Nếu tên giống hoặc gần giống → merge toàn bộ object từ file JSON vào dòng tương ứng của JSONL
- Đảm bảo **không merge nhầm** giữa các doanh nghiệp không liên quan


## Conversation Detail

### User
Cung cấp một object JSON mẫu và hỏi:

> “Đây là cú pháp của một dòng data trong file .json của tôi, bạn có thể list các tên object ra không?”

---

### ChatGPT
Liệt kê đầy đủ các key (object name) trong JSON.  
Đề xuất hỗ trợ thêm:
- Trích key bằng Python
- Xử lý nhiều dòng JSON
- Xuất dữ liệu sang CSV hoặc README.md

---

### User
Cung cấp hai object thuộc hai file khác nhau:

- File 1: `Tên doanh nghiệp`
- File 2: `company_name`

Yêu cầu:

> So sánh hai object này, nếu cụm từ giống hoặc gần giống thì ghép các object còn lại của file 2 vào file 1 cho từng dòng tương ứng. Tôi muốn một đoạn code Python hoàn chỉnh.

---

### ChatGPT
Xác định đây là bài toán **fuzzy string matching + data merge**.  
Đề xuất giải pháp:
- Chuẩn hóa chuỗi (bỏ dấu tiếng Việt, ký tự đặc biệt)
- Dùng thư viện `rapidfuzz`
- So sánh độ tương đồng
- Merge dữ liệu nếu vượt ngưỡng

Cung cấp script Python hoàn chỉnh cho case **JSON + JSON**.

---

### User
Hỏi tiếp:

> “Thế tôi có file 1 là jsonl còn file 2 là json thì như thế nào?”

---

### ChatGPT
Giải thích sự khác nhau giữa JSON và JSONL:
- JSON: load toàn bộ 1 lần
- JSONL: đọc từng dòng

Cập nhật script để:
- Đọc file 1 theo từng dòng JSONL
- Giữ nguyên logic fuzzy matching
- Output vẫn là JSONL

---

### User
Phát hiện lỗi nghiêm trọng và gửi ví dụ thực tế:

```json
"Tên doanh nghiệp": "Công viên thành công"
"company_name": "Công Ty TNHH Một Thành Viên Thanh Hương Technology"
"_match_score": 100.0

---
# Thành viên 2: Hậu
### Date: 2026-01-08

**Task:** Xây dựng hệ thống crawl hồ sơ doanh nghiệp (BizInfo & Review 360)

**User:** Tôi cần một số website có thể crawl dữ liệu doanh nghiệp, phục vụ bài toán BizInfo & Review 360, bao gồm thông tin pháp lý (nguồn sạch) và review/bình luận (nguồn bẩn). Thách thức là merge dữ liệu dựa trên tên công ty hoặc mã số thuế.

**AI (ChatGPT):** Gợi ý các nguồn dữ liệu doanh nghiệp phổ biến tại Việt Nam (nguồn danh bạ doanh nghiệp, trang thông tin công ty, trang review), đồng thời phân tích kiến trúc list–detail crawler và vấn đề data merging theo tên công ty/MST.

---

### Date: 2026-01-08

**Task:** Viết code crawler list–detail và lưu CSV

**User:** Hãy viết code crawl, lưu dữ liệu dạng dòng CSV, có log đang crawl tới trang nào, dòng nào, và có thể chọn bắt đầu crawl từ dòng bất kỳ để resume.

**AI (ChatGPT):** Cung cấp skeleton crawler Python (requests + BeautifulSoup), hỗ trợ resume bằng START_ROW, log chi tiết tiến trình crawl, và cấu trúc CSV phù hợp cho dữ liệu doanh nghiệp.

---

### Date: 2026-01-08

**Task:** Debug lỗi crawler chạy nhưng CSV trống

**User:** Code vẫn chạy nhưng file CSV trống. Kiểm tra thì `len(companies)=0`.

**AI (ChatGPT):** Phân tích nguyên nhân selector HTML không khớp DOM thực tế. Hướng dẫn kiểm tra lại cấu trúc `div.search-results` và thẻ `<a href>` chứa link công ty.

---

### Date: 2026-01-08

**Task:** Debug lỗi không tìm thấy công ty do DOM phức tạp

**User:** Thông tin công ty nằm trong `div.search-results`, bên trong là thẻ `<a>` chứa tên, và các thẻ `<p>` khác. Code hiện tại không parse được.

**AI (ChatGPT):** Điều chỉnh selector BeautifulSoup cho đúng DOM, giải thích cách duyệt từng block kết quả, lấy tên và link chi tiết chính xác.

---

### Date: 2026-01-08

**Task:** Crawl trang chi tiết và kiểm soát việc theo link

**User:** Tôi muốn chỉ vào link chi tiết 1 lần, không theo các link con bên trong. Trang chi tiết có cấu trúc `div.jumbotron`.

**AI (ChatGPT):** Viết hàm `crawl_detail_page()` chỉ parse text trong `div.jumbotron`, không crawl link con, trích xuất các trường: tên công ty, MST, địa chỉ, đại diện pháp luật, ngày cấp phép, trạng thái.

---

### Date: 2026-01-08

**Task:** Debug lỗi timeout và mất tên công ty trong CSV

**User:** Một số trang bị `Read timed out`. Có trang in ra tên trong log nhưng khi ghi CSV thì mất tên.

**AI (ChatGPT):** Phân tích hai lỗi chính: (1) request bị treo do thiếu timeout/retry; (2) logic lấy tên công ty dựa vào text line không ổn định. Đề xuất retry mechanism, lấy tên trực tiếp từ DOM (`h4 span[title]`) và chỉ ghi CSV khi crawl detail thành công.

---

### Date: 2026-01-08

**Task:** Chuẩn hóa chương trình chính (main loop)

**User:** Hãy viết lại chương trình chính tương ứng với code đã sửa.

**AI (ChatGPT):** Cung cấp main loop chuẩn crawler production: mở CSV một lần, log rõ ROW, skip khi detail fail, đảm bảo không mất dữ liệu và có thể resume bằng START_ROW.

---

### Date: 2026-01-08

**Task:** Mở rộng crawler để crawl nhiều page list

**User:** Tôi muốn thêm vòng lặp để crawl nhiều page theo cấu trúc `?page=18`.

**AI (ChatGPT):** Thiết kế vòng lặp page–row toàn cục, tách `BASE_DOMAIN` và tham số page, đảm bảo link detail đúng, hỗ trợ resume theo dòng và log rõ PAGE | ROW.

---

### Date: 2026-01-08

**Task:** Refactor file code hoàn chỉnh

**User:** Đây là toàn bộ file hiện tại, hãy sửa lại.

**AI (ChatGPT):** Phát hiện lỗi ghép URL (`BASE_URL` chứa `?page=`), refactor thành `BASE_DOMAIN`, chuẩn hóa hàm crawl list theo page, giữ nguyên logic crawl detail, và viết lại chương trình chính crawl nhiều page ổn định.

---

### Date: 2026-01-10
**Task:** Tìm nguồn dữ liệu để crawl thông tin doanh nghiệp (Thông tin pháp lý, Thuế, Review)

**User:** Ngoài các trang tratencongty, reviewcongty, thongtincongty, careerlink thì còn trang web nào có thể crawl thông tin công ty không?

**AI (ChatGPT):**  
Đề xuất thêm nhiều nguồn dữ liệu trong và ngoài nước như Masothue.vn, Doanhnghiepmoi.vn, Hosocongty.vn, Sosanhcongty.com, JobStreet, OpenCorporates… Đồng thời phân loại rõ theo mục tiêu dữ liệu (thông tin pháp lý, review, dữ liệu quốc tế) và lưu ý về giới hạn dữ liệu thuế chi tiết do ràng buộc pháp lý.

---

### Date: 2026-01-10
**Task:** Thiết kế crawler cho website hsctvn.com

**User:** Hãy viết cho tôi code để crawl dữ liệu từ trang web hsctvn.com, có phân trang, có trang chi tiết, hỗ trợ resume, yêu cầu dùng async hoặc multithreading.

**AI (ChatGPT):**  
Thiết kế kiến trúc crawler 2 tầng (list page → detail page) sử dụng `aiohttp + asyncio`, có cấu hình `START_PAGE`, `END_PAGE`, `START_ROW`, sử dụng Semaphore để giới hạn concurrent requests, ghi CSV từng dòng để tránh mất dữ liệu khi bị ngắt.

---

### Date: 2026-01-10
**Task:** Tinh chỉnh selector HTML theo cấu trúc thực tế

**User:** Tôi gửi ảnh HTML của trang danh sách và trang chi tiết, hãy sửa code để lấy đúng thẻ.

**AI (ChatGPT):**  
Phân tích cấu trúc HTML thực tế (`ul.hsdn`, `ul.hsct`), sửa selector chính xác để lấy link công ty và thông tin chi tiết. Áp dụng cách parse dựa trên nhãn tiếng Việt thay vì vị trí thẻ nhằm tăng độ ổn định khi giao diện thay đổi.

---

### Date: 2026-01-10
**Task:** Bổ sung retry và log HTTP status

**User:** Thêm cho tôi phần retry khi timeout và in HTTP (200, 404, …).

**AI (ChatGPT):**  
Bổ sung cơ chế retry có kiểm soát cho timeout và lỗi 5xx, không retry với 404. In log HTTP status cho từng request, thêm backoff nhẹ giữa các lần retry để tránh gây tải đột ngột cho server.

---

### Date: 2026-01-10
**Task:** Crawl đầy đủ thông tin công ty (tiếng Việt có dấu)

**User:** Sửa `parse_company_page` để lấy full data vì trang còn nhiều thông tin khác, và đảm bảo tiếng Việt có dấu.

**AI (ChatGPT):**  
Viết lại hàm parse theo hướng đọc nhãn–giá trị (label → value), lấy đầy đủ các trường như tên công ty, tên viết tắt, mã số thuế, địa chỉ, đại diện pháp luật, điện thoại, email, ngày cấp, trạng thái. Giữ nguyên Unicode UTF-8 để bảo toàn tiếng Việt có dấu.

---

### Date: 2026-01-10
**Task:** Debug lỗi ghi CSV (`dict contains fields not in fieldnames`)

**User:** Khi chạy thì gặp lỗi ValueError do dict chứa field không có trong fieldnames.

**AI (ChatGPT):**  
Chỉ ra nguyên nhân do schema dữ liệu không đồng bộ giữa `DictWriter` và dict trả về. Hướng dẫn sửa bằng cách định nghĩa `FIELDNAMES` đầy đủ và dùng thống nhất cho mọi lần ghi CSV.

---

### Date: 2026-01-10
**Task:** Sửa và chuẩn hóa toàn bộ script crawl

**User:** Đây là full code hiện tại của tôi, hãy sửa toàn bộ giúp tôi.

**AI (ChatGPT):**  
Cung cấp phiên bản code hoàn chỉnh, đã sửa tất cả lỗi schema, đồng bộ fieldnames, giữ async + retry + resume, đảm bảo chạy ổn định và phù hợp nộp đồ án.

---

### Date: 2026-01-10
**Task:** Tránh bị chặn khi crawl

**User:** Có thể bị chặn không, nếu có thêm delay 0.5s.

**AI (ChatGPT):**  
Giải thích nguy cơ bị chặn (429, 403), hướng dẫn thêm delay hợp lý sau mỗi request chi tiết bằng `await asyncio.sleep(0.5 + random.uniform(0, 0.3))` để tránh pattern bot.

---
### Date: 2026-01-10
**Task**: Xử lý CSV để loại bỏ cột trống và tự động làm sạch khi crawl

**User**: Tôi muốn xóa luôn cột trống giữa ,,, chỉ để lại cột trước và sau.

**AI (ChatGPT)**:
Giải thích rằng ,, trong CSV đại diện cho cột trống, không phải dấu phẩy liên tiếp trong văn bản. Đề xuất dùng module csv của Python để đọc, loại bỏ cột trống và xuất CSV mới, đảm bảo không phá hỏng dấu phẩy trong các chuỗi có nháy kép.

---

### Date: 2026-01-10
**Task**: Áp dụng logic làm sạch code trong code crawl

***User**: Tôi muốn thêm logic [col for col in lines if col.strip() != ''] ngay lúc viết dữ liệu vào file trong code crawl. Đây là code của tôi, hãy xem và sửa.

**AI (ChatGPT)**:
Gợi ý tích hợp lọc cột trống ngay khi ghi CSV trong vòng lặp crawl. Giải thích:
- Mỗi dòng dữ liệu tự động loại bỏ cột trống ngay khi crawl xong.
- Dấu phẩy trong các cột khác, ví dụ địa chỉ, vẫn được giữ nguyên.
- Vẫn giữ delay giữa các request để tránh bị chặn, đảm bảo crawl ổn định.

---
### Date: 2026-01-11

**Task**: Phân tích nguyên nhân crawl chậm và đề xuất chiến lược tăng tốc an toàn

**User**:
Có cách nào crawl nhanh dữ liệu không. tôi đang dùng code này [code] thì chạy khá lâu

**AI (ChatGPT)**:
Phân tích pipeline crawl hiện tại và xác định các điểm nghẽn hiệu năng. Chỉ ra rằng tốc độ chậm chủ yếu đến từ việc mỗi công ty cần một request riêng cho trang chi tiết, có sleep sau mỗi bản ghi, không tái sử dụng kết nối mạng và ghi dữ liệu xuống file CSV theo từng dòng.

Đề xuất các hướng tối ưu theo mức độ rủi ro tăng dần, trong đó nhấn mạnh nhóm giải pháp an toàn gồm: sử dụng session để tái sử dụng TCP connection, giảm sleep không cần thiết bằng cách chuyển sleep theo page, và ghi CSV theo batch để giảm chi phí I/O. Đồng thời nêu rõ các phương án tăng tốc mạnh hơn (song song, bỏ crawl detail) để người dùng lựa chọn tùy theo mức ưu tiên giữa tốc độ và độ ổn định.

---
### Date: 2026-01-11
**Task**: Tái cấu trúc code crawl để tăng tốc nhưng vẫn đảm bảo ổn định

**User**:
Hãy sửa lại dựa trên code của tôi, ghi lại cho tôi đoạn code hoàn chỉnh để crawl

**AI (ChatGPT)**:
Tiến hành chỉnh sửa trực tiếp trên cấu trúc code người dùng cung cấp, giữ nguyên logic crawl dữ liệu và các tham số kiểm soát (start page, end page, resume theo dòng). Áp dụng các tối ưu an toàn đã đề xuất trước đó, bao gồm việc sử dụng session HTTP, điều chỉnh chiến lược delay, và ghi dữ liệu theo batch.

Kết quả là một phiên bản code hoàn chỉnh, có thể chạy ngay, cho tốc độ cải thiện rõ rệt so với phiên bản ban đầu nhưng không làm tăng đáng kể nguy cơ bị chặn. Đồng thời định hướng rõ các bước mở rộng tiếp theo nếu cần crawl dữ liệu quy mô lớn hơn hoặc tăng tốc mạnh hơn trong tương lai.

---

### Date: 2026-01-12

**Task**: Làm sạch và chuẩn hoá dữ liệu CSV crawl được (file clean data)

**User**:
Data crawl ra [data] có nhiều lỗi nhẹ: lệch cột, dấu " dư, ký tự HTML rác, định dạng ngày không thống nhất (ví dụ 5/6/2025, 23/06/2025 (), dấu chấm cuối tên công ty. Yêu cầu làm sạch nhưng không phá cấu trúc dữ liệu.

**AI (ChatGPT)**:
Phân tích dữ liệu ở mức raw CSV, xác định nguyên nhân chính là do dữ liệu HTML bẩn và regex xử lý ngày quá chặt. Đề xuất quy trình clean theo hướng ETL chuẩn: đọc từng dòng, giữ schema cố định 7 cột, không dùng pandas, không parse datetime.

Xây dựng các hàm làm sạch độc lập:
- Clean text thô (loại bỏ "", ký tự rác, chuẩn hoá khoảng trắng).
- Chuẩn hoá tên công ty, chỉ bỏ dấu chấm ở cuối chuỗi.
- Chuẩn hoá ngày bằng cách trích ngày hợp lệ đầu tiên trong chuỗi và đưa về DD/MM/YYYY.

Sửa lỗi logic đọc file (file không có header nhưng code giả định có header dẫn đến mất dòng đầu). Kết quả là một script clean độc lập, xử lý được toàn bộ các trường hợp dữ liệu bẩn đã quan sát, cho đầu ra CSV ổn định, Excel mở trực tiếp, sẵn sàng cho các bước NLP/ML.

---

### Date: 2026-01-12

**Task**: Áp dụng logic clean trực tiếp vào code crawl chính để dữ liệu sạch ngay từ đầu

**User**:
Đây là code crawl của tôi [code]. Tôi muốn data crawl ra có dạng giống như đã clean [data]. Hãy sửa lại

**AI (ChatGPT)**:
Tiến hành chỉnh sửa trực tiếp trên cấu trúc code người dùng cung cấp, giữ nguyên toàn bộ logic crawl, phân trang, resume theo dòng và chiến lược delay để tránh bị chặn.
- Áp dụng toàn bộ logic clean đã xây dựng vào pipeline crawl:
- Loại bỏ cột MST khỏi CSV (do không crawl được vì là ảnh).
- Chuẩn hoá tên công ty, địa chỉ, người đại diện ngay khi parse HTML.
- Chuẩn hoá ngày tháng bằng regex linh hoạt, xử lý ký tự rác đi kèm.
- Không xoá cột rỗng bằng filter để tránh lệch schema.
- Ghi CSV với utf-8-sig và QUOTE_ALL để đảm bảo an toàn khi mở bằng Excel.

---

### Date: 2026-01-12
**Task**: Xây dựng logic crawl dữ liệu doanh nghiệp từ website infodoanhnghiep.com dựa trên pipeline async hiện có.

**User**:
Yêu cầu crawl website infodoanhnghiep.com theo trình tự:
-Lấy link từ trang danh sách
-Truy cập trang chi tiết
-Trích xuất các trường: tên doanh nghiệp, tên giao dịch, mã số thuế, địa chỉ, tình trạng hoạt động, ngày cấp giấy phép, lĩnh vực kinh doanh.

**AI (ChatGPT)**:
- Phân tích HTML trang danh sách (div.company-item) để xác định selector lấy link chi tiết.
- Tái sử dụng pipeline aiohttp + asyncio + semaphore + batch write từ hsctvn.com nhằm đảm bảo tốc độ và độ ổn định.
- Thiết kế parser trang chi tiết dựa trên:
    - Heading chính (h1) cho tên doanh nghiệp
    - schema.org (itemprop="taxID", itemprop="address") cho MST và địa chỉ
    - Bảng thông tin dạng label – value (div.responsive-table-cell) cho các trường còn lại.
    - Áp dụng clean text và chuẩn hóa ngày tháng ngay trong bước parse để dữ liệu sạch từ đầu.

---

### Date: 2026-01-12
**Task** : Khắc phục lỗi không trích xuất được trường Tên giao dịch trên trang chi tiết doanh nghiệp.

**User**:
Phản hồi rằng trường Tên giao dịch bị rỗng sau khi crawl.

**AI (ChatGPT)**:
- Kiểm tra lại HTML thực tế của infodoanhnghiep.com.
- Phát hiện website không sử dụng itemprop="alternateName" cho trường Tên giao dịch như giả định ban đầu.
- Xác định Tên giao dịch được render dưới dạng label – value trong bảng div.responsive-table-cell.
Giải pháp:
- Chuyển sang label-based parsing:
- Duyệt các div.responsive-table-cell
- Khi gặp label "Tên giao dịch", lấy nội dung của cell kế tiếp làm giá trị.
- Đồng bộ logic với các trường Ngày cấp giấy phép và Tình trạng hoạt động.

---

### Date: 2026-01-16

**Task:** Phát hiện và loại bỏ dữ liệu trùng lặp trong quá trình crawl nhằm đảm bảo dữ liệu đầu ra sạch và nhất quán

**User:**
Đây là code crawl của tôi [code]. Sau khi crawl xong, dữ liệu CSV phát sinh nhiều dòng trùng nhau. Tôi muốn áp dụng logic detect duplicate và xóa trực tiếp, giữ lại dữ liệu hợp lệ duy nhất và ghi lại vào file gốc.

**AI (ChatGPT)**:
Tiến hành xây dựng và áp dụng logic xử lý duplicate dựa trên đặc trưng dữ liệu doanh nghiệp, không làm thay đổi cấu trúc crawl hiện tại.

Xác định khóa trùng lặp dựa trên tổ hợp các cột có tính định danh cao (tên doanh nghiệp, mã số thuế, địa chỉ).

Sử dụng cơ chế drop_duplicates với keep="first" để giữ lại bản ghi hợp lệ đầu tiên.

Không xóa theo từng cột đơn lẻ nhằm tránh mất dữ liệu của các doanh nghiệp khác nhau có tên tương tự.

Thực hiện reset index sau khi loại bỏ duplicate để đảm bảo tính nhất quán của DataFrame.

Ghi đè trực tiếp kết quả đã clean vào file CSV gốc, giữ encoding utf-8-sig và không sinh thêm cột index.

Logic xử lý duplicate được tách biệt, dễ tái sử dụng và không ảnh hưởng đến pipeline crawl async hiện có.


### Date: 2026-01-22

**Task:** Hợp nhất dữ liệu doanh nghiệp từ nhiều nguồn CSV

**User:**
Tôi muốn ghép các dataframe thành một DF hoàn chỉnh gồm các trường pháp lý doanh nghiệp (tên, MST, địa chỉ, tình trạng hoạt động, ngành nghề, …), loại bỏ các cột không cần thiết như URL, thời gian crawl. Yêu cầu giữ lại cả các dòng thiếu thông tin (outer merge), cột thiếu để trống.

**AI (ChatGPT):**
Xác nhận yêu cầu merge theo schema chuẩn, sử dụng outer join, ưu tiên dữ liệu nguồn chính, dữ liệu thiếu để NaN.

---
### Date: 2026-01-22

**Task:** Bổ sung doanh nghiệp từ nguồn dữ liệu thứ hai

**User:**
Muốn thêm toàn bộ công ty từ df2 vào kết quả cuối. Nếu df1 không có thì vẫn giữ, các cột không tồn tại trong df1 để trống.

**AI (ChatGPT):**
Đề xuất merge df1 và df2 bằng khóa chung (MST), dùng combine_first để ưu tiên nguồn chính nhưng không làm mất dữ liệu nguồn phụ.

---
### Date: 2026-01-22

**Task:** Debug lỗi merge DataFrame

**User:**
Gặp lỗi KeyError: 'mst_clean' khi chuẩn hóa cột “Mã số thuế” sau khi merge hai dataframe.

**AI (ChatGPT):**
Chỉ ra lỗi do tham chiếu cột không tồn tại trong merged, hướng dẫn sử dụng đúng tên cột hậu merge (_df1, _df2) hoặc tái sử dụng mst_key.

---
### Date: 2026-01-22

**Task:** Làm sạch dữ liệu ngành nghề kinh doanh

**User:**
Yêu cầu loại bỏ chuỗi “(Xem danh sách)” trong cột Ngành nghề kinh doanh.

**AI (ChatGPT):**
Đề xuất xử lý bằng str.replace() hoặc regex để làm sạch text mà không ảnh hưởng dữ liệu còn lại.

---
### Date: 2026-01-22

**Task:** Kiểm tra số phần tử trong file JSON

**User:**
Muốn có đoạn code mở file JSON và kiểm tra số phần tử bên trong.


Thành viên 3: Duy
================================================================================
CONVERSATION LOG - Web Scraping Script Development
================================================================================
Project: Crawl_data_SEG301.py
Target Website: thongtincongty.vn
Date Range: 2026-01-09 to 2026-01-11
================================================================================

[2026-01-09 - Initial Issue]
User Request: "toi chon lay tu dong thi chi co duoc 20 cong ty, bay giof toi muon lay tu dong cac cong ty khac co duoc khong"
Translation: Auto-fetch only gets 20 companies, wants to fetch more automatically

Problem Identified:
- Script limited to ~20 companies per run
- Homepage pagination not working properly
- Need automatic fetching for larger datasets

[2026-01-09 - First Error Encountered]
Error Message: "404 Client Error: Not Found for url: https://thongtincongty.vn/page/2"
Context: Auto-fetch from homepage option

Root Cause Analysis:
- Website does not support pagination beyond page 1
- URLs like /page/2/ return 404 Not Found
- Homepage scraping fails when trying to access page 2+

Solution Implemented:
- Added status_code check before raise_for_status()
- Stop pagination early when 404 detected
- Fallback to keyword search to supplement links

Code Changes in get_company_links_from_homepage():
  if resp.status_code == 404 and page > 1:
      print(f"  Trang {url} tra ve 404, dung phan trang trang chu.")
      break

[2026-01-09 - Second Error Encountered]
Error Message: "404 Client Error: Not Found for url: https://thongtincongty.vn/page/2?s=a"
Context: Search function trying to paginate results

Root Cause Analysis:
- Search pagination also returns 404 for page 2+
- Same issue as homepage pagination
- Causes crash when iterating through keyword searches

Solution Implemented:
- Applied same 404 detection logic to search_companies()
- Stop pagination gracefully
- Keep results from page 1

Code Changes in search_companies():
  if resp.status_code == 404 and page > 1:
      print(f"  Trang {search_url} tra ve 404, dung phan trang tim kiem.")
      break

[2026-01-09 - Data Persistence Issue]
User Request: "sao du lieu khong duoc luu lai, ma moi lan crawl thi ra du lieu moi ma khong luu data cu"
Translation: Data not being saved, new crawl overwrites old data

Problem Identified:
- Each new crawl session overwrites previous CSV file
- is_first=True always opens file in write mode 'w'
- Previous company data lost on each run

Root Cause:
- In save_data(): mode = 'w' if is_first else 'a'
- First company of new session always uses write mode
- No check if file already exists with previous data

Solution Implemented:
- Check if file exists before deciding mode
- Only use 'w' mode if file does not exist
- Use 'a' (append) mode when file already has data
- Skip header when appending

Code Changes in save_data():
  file_exists = filepath.exists()
  mode = 'w' if (is_first and not file_exists) else 'a'
  write_header = (is_first and not file_exists) or not file_exists

[2026-01-11 - Division by Zero Error]
Error Message: "ZeroDivisionError: integer division or modulo by zero"
Stack Trace: extra = search_companies(kw, (max_companies - len(urls)) // (5 - len(keywords)), max_pages=5)

Root Cause Analysis:
- keywords list has 5 elements
- Loop iterates through all keywords
- Expression: (5 - len(keywords)) evaluates to (5 - 5) = 0
- Division by zero when calculating 'needed' amount

Solution Implemented:
- Use enumerate() to track keyword index
- Calculate remaining keywords: len(keywords) - idx
- Use max(1, ...) to ensure divisor is at least 1
- Prevents division by zero in all cases

Code Changes in Option 5:
  for idx, kw in enumerate(keywords):
      needed = (max_companies - len(urls)) // max(1, len(keywords) - idx)
      extra = search_companies(kw, needed, max_pages=5)

[2026-01-11 - Scalability Enhancement]
User Request: "moi lan chi toi da 20 cong ty, co cach nao tang nang xuat crawl len nhieu cong ty hon khong"
Translation: Maximum 20 companies per run, need to increase crawling capacity

Problem Analysis:
- Homepage only provides limited links
- Single keyword search yields few results
- Pagination broken (404 errors)
- Need multiple strategies to gather more links

Solution Strategy 1 - Expanded Keyword Pool:
- Increased from 10 to 25 keywords
- Added Vietnamese terms: "cong ty", "doanh nghiep", "tap doan"
- Added business types: "cua hang", "chi nhanh", "van phong"
- Added facility types: "nha hang", "khach san", "sieu thi", "buu cuc"

Updated keyword_pool in get_company_links_from_homepage():
  keyword_pool = [
      "a", "e", "i", "o", "u", "1", "2", "3", "c", "t",
      "cong ty", "doanh nghiep", "tap doan", "cua hang", "chi nhanh",
      "van phong", "nha hang", "quan", "buu cuc", "tram",
      "sieu thi", "khach san", "cong xuong", "kho", "trung tam"
  ]

Solution Strategy 2 - Geographic Search:
- Created new function: search_companies_by_location(province, max_results)
- Search by province/city names
- Target 10 major Vietnamese locations
- Diversifies company sources

New function added:
  def search_companies_by_location(province, max_results=10):
      search_url = f"https://thongtincongty.vn/?s={province}"
      # Parse links from search results
      # Filter for /ma-so-thue/ paths
      return links

Province list: "Ha Noi", "TP.HCM", "Da Nang", "Hai Phong", "Can Tho", "Binh Duong", "Dong Nai", "Long An", "Quang Ninh", "Bac Ninh"

Solution Strategy 3 - New Menu Options:
Updated main menu with 5 options:
  1. Use predefined URL list in code
  2. Manual URL input
  3. Auto-fetch from homepage + multi-keyword search (default: 100 companies)
  4. Search by specific keyword (default: 100 companies)
  5. Combined search: multi-province + multi-keyword (default: 150 companies)

Option 3 Changes:
- Default increased from 50 to 100 companies
- Uses expanded 25-keyword pool
- Falls back to keyword search when homepage insufficient

Option 4 Changes:
- Default increased from 50 to 100 companies
- Allows user-specified keyword
- Attempts pagination (stops at 404)

Option 5 Implementation (NEW - Highest Capacity):
- Default 150 companies
- Searches 10 provinces first
- Supplements with 5 business-type keywords
- Distributes quota across sources
- Best option for large-scale crawling

[2026-01-11 - Feature Summary]
Completed Features:

1. Error Handling:
   - 404 detection and graceful pagination stop
   - No crashes on pagination failures
   - Preserves partial results

2. Data Management:
   - Append mode preserves previous data
   - Deduplication by tax code (ma_so_thue)
   - Retry mechanism for file lock (PermissionError)
   - Backup file creation when main file locked
   - CSV written to E:/crawled_data/

3. Link Collection Strategies:
   - Homepage scraping (page 1 only)
   - Multi-keyword search (25 keywords)
   - Geographic search (10 provinces)
   - Combined multi-source approach

4. Performance Optimizations:
   - 1 second delay between company crawls
   - 0.5 second delay between page requests
   - Browser-like headers to avoid blocking
   - 30 second timeout per request

5. User Interface:
   - 5 menu options for different use cases
   - Configurable company count per option
   - Progress tracking: [current/total]
   - Success/failure statistics
   - Final summary report

================================================================================
CAPACITY COMPARISON
================================================================================

Before Optimization:
- Maximum: ~20 companies per session
- Single source (homepage)
- Crashes on pagination errors
- Overwrites previous data

After Optimization:
- Option 3: Up to 100 companies (homepage + 25 keywords)
- Option 4: Up to 100 companies (user keyword)
- Option 5: Up to 150+ companies (10 provinces + 5 keywords)
- No crashes, graceful error handling
- Preserves all previous data
- Auto-deduplication by tax code

Performance Increase: 7.5x (from 20 to 150+ companies)

================================================================================
KEY FUNCTIONS
================================================================================

get_company_links_from_homepage(max_links, max_pages):
  Purpose: Fetch company links from homepage
  Features:
    - Pagination with 404 detection
    - Fallback to keyword search
    - Deduplication of links
  Returns: List of company URLs

search_companies(keyword, max_results, max_pages):
  Purpose: Search companies by keyword
  Features:
    - Pagination with 404 handling
    - Filters /ma-so-thue/ and /cong-ty/ paths
    - Configurable result limit
  Returns: List of company URLs

search_companies_by_location(province, max_results):
  Purpose: Search companies by province/city
  Features:
    - Single-page search
    - Geographic diversity
    - Quick link collection
  Returns: List of company URLs

parse_company_info(html, url):
  Purpose: Extract company data from HTML
  Fields Extracted:
    - Ten don vi / Ten doanh nghiep
    - Ma so thue
    - Ma so thue cu
    - Dia chi
    - Trang thai
    - Co quan thue
    - Phuong phap tinh thue
    - Nganh nghe
    - Chuong khoan
  Returns: Dictionary with company info

save_data(data, filename, is_first):
  Purpose: Save company data to CSV
  Features:
    - Append mode (preserves old data)
    - Deduplication by tax code
    - Retry on PermissionError (3 attempts)
    - Backup file on persistent lock
    - UTF-8-sig encoding for Excel compatibility
  Output: E:/crawled_data/all_companies_data.csv

crawl_requests(url):
  Purpose: Fetch and parse single company page
  Method: HTTP requests (no browser needed)
  Headers: Mimics Chrome browser
  Timeout: 30 seconds
  Returns: Company data dictionary

================================================================================
ERROR RESOLUTION TIMELINE
================================================================================

Issue 1: Homepage 404 Error
  Time: 2026-01-09
  Status: RESOLVED
  Method: Status code check + early break

Issue 2: Search 404 Error  
  Time: 2026-01-09
  Status: RESOLVED
  Method: Applied same fix as Issue 1

Issue 3: Data Overwrite
  Time: 2026-01-09
  Status: RESOLVED
  Method: File existence check + append mode

Issue 4: Division by Zero
  Time: 2026-01-11
  Status: RESOLVED
  Method: enumerate() + max(1, ...) guard

Issue 5: Low Company Limit
  Time: 2026-01-11
  Status: RESOLVED
  Method: Multi-strategy link collection

================================================================================
USAGE RECOMMENDATIONS
================================================================================

For Small Datasets (< 50 companies):
  Use Option 3 or 4
  Set limit to 50
  Single keyword search sufficient

For Medium Datasets (50-100 companies):
  Use Option 3
  Set limit to 100
  Leverages 25-keyword pool

For Large Datasets (100+ companies):
  Use Option 5 (RECOMMENDED)
  Set limit to 150 or higher
  Combines geographic + keyword search
  Best performance and diversity

General Tips:
  - Close CSV file before running script
  - Use Option 5 for maximum efficiency
  - Check E:/crawled_data/ for output
  - Script auto-creates directory if missing
  - Duplicates automatically filtered by tax code
  - Can run multiple times to accumulate data

================================================================================
FILE STRUCTURE
================================================================================

Output Directory: E:/crawled_data/
Main Output File: all_companies_data.csv
Backup Files: all_companies_data_backup_[timestamp].csv

CSV Format:
  - Encoding: UTF-8-sig (Excel compatible)
  - Delimiter: Comma
  - Headers: Ten cong ty, URL, Thoi gian crawl, ma_so_thue, dia_chi, etc.
  - One row per company
  - Duplicates filtered by ma_so_thue field

================================================================================



## END OF AI INTERACTION LOG
