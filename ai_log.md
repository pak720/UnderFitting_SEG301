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

# AI INTERACTION LOG

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

**Task**: Phát hiện và loại bỏ dữ liệu trùng lặp trong quá trình crawl nhằm đảm bảo dữ liệu đầu ra sạch và nhất quán

**User**:
Đây là code crawl của tôi [code]. Sau khi crawl xong, dữ liệu CSV phát sinh nhiều dòng trùng nhau. Tôi muốn áp dụng logic detect duplicate và xóa trực tiếp, giữ lại dữ liệu hợp lệ duy nhất và ghi lại vào file gốc.

**AI (ChatGPT)**:
Tiến hành xây dựng và áp dụng logic xử lý duplicate dựa trên đặc trưng dữ liệu doanh nghiệp, không làm thay đổi cấu trúc crawl hiện tại.

Xác định khóa trùng lặp dựa trên tổ hợp các cột có tính định danh cao (tên doanh nghiệp, mã số thuế, địa chỉ).

Sử dụng cơ chế drop_duplicates với keep="first" để giữ lại bản ghi hợp lệ đầu tiên.

Không xóa theo từng cột đơn lẻ nhằm tránh mất dữ liệu của các doanh nghiệp khác nhau có tên tương tự.

Thực hiện reset index sau khi loại bỏ duplicate để đảm bảo tính nhất quán của DataFrame.

Ghi đè trực tiếp kết quả đã clean vào file CSV gốc, giữ encoding utf-8-sig và không sinh thêm cột index.

Logic xử lý duplicate được tách biệt, dễ tái sử dụng và không ảnh hưởng đến pipeline crawl async hiện có.

## END OF AI INTERACTION LOG
