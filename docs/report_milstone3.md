# Báo cáo Milestone 3 — Final Product
**Môn học:** SEG301 – Search Engines & Information Retrieval
**Nhóm:** UnderFitting
**Thành viên:** Võ Minh Huy (QE190059) · Thân Phúc Hậu (QE190002) · Nguyễn Lê Anh Duy (QE190134)
**Deadline:** Tuần 10

---

## 1. Tổng quan

Milestone 3 mở rộng hệ thống từ BM25 thuần túy (M2) lên sản phẩm hoàn chỉnh:

| Thành phần | Mô tả |
|---|---|
| **Vector Search** | Tìm kiếm ngữ nghĩa qua FAISS + Sentence-Transformers |
| **Hybrid Search** | Kết hợp điểm BM25 + Vector theo weighted fusion |
| **Web Interface** | Streamlit với Search, Filter, Pagination |
| **Evaluation** | Precision@10, Recall@10, MRR trên 20 queries |

Dữ liệu: **1,620,401 tài liệu** doanh nghiệp Việt Nam, định dạng JSONL.

---

## 2. Tính năng AI — Vector Search (3đ)

### 2.1 Mô hình Embedding

| Thành phần | Chi tiết |
|---|---|
| Model | `intfloat/multilingual-e5-base` |
| Embedding dim | 768 |
| Prefix | `passage: <text>` khi index · `query: <text>` khi search |
| Device | CUDA (GPU RTX 3050) + CPU fallback |
| FP16 | Tuỳ chọn (`--fp16`), ~2× tốc độ encode |

Model `multilingual-e5-base` được chọn vì hỗ trợ tiếng Việt tốt và dùng kiến trúc **asymmetric retrieval** (query prefix ≠ passage prefix), phù hợp cho bài toán tìm kiếm.

### 2.2 Chiến lược Embedding đa trường (4 slots/doc)

Mỗi tài liệu được embed thành **4 vector riêng biệt**, lưu ở 4 FAISS slots liên tiếp:

| Slot | Trường | Mục đích |
|---|---|---|
| 0 | Tên doanh nghiệp + Tên giao dịch | Query tên công ty cụ thể |
| 1 | Ngành nghề kinh doanh | Query theo lĩnh vực |
| 2 | Tỉnh/thành (trích từ cuối địa chỉ) | Query theo địa lý |
| 3 | Full-doc (name + industry + province) | Query đa khái niệm |

**Chiến lược tìm kiếm:**
- Query **không có địa danh** → `MAX` score qua cả 4 slots → trường chuyên biệt thắng
- Query **có địa danh** (vd: "nhà hàng hà nội") → chỉ dùng **slot 3 (full-doc)** → buộc cả hai khái niệm phải cùng xuất hiện, tránh single-field domination

### 2.3 FAISS Index

| Tham số | Giá trị |
|---|---|
| Index type | `IndexIVFPQ` (N ≥ 9,984) / `IndexFlatIP` (dataset nhỏ) |
| Metric | Cosine similarity (L2-normalised inner product) |
| nlist | 256 |
| M (sub-quantizers) | 32 (768 / 32 = 24 ✓) |
| nprobe | 32 |
| Kích thước (1.62M docs × 4 fields) | **261 MB** |

`IndexIVFPQ` giảm ~20× so với `IndexFlatIP` (~5GB → 261MB) với tốc độ tìm kiếm ~50ms.

### 2.4 Tối ưu RAM khi build index

Vấn đề: 1.62M docs × 4 fields × 768 dim × 4 bytes ≈ **20GB** nếu giữ toàn bộ trong RAM.

Giải pháp:
- **Streaming binary file** (`build_embeddings.bin`): mỗi batch được ghi xuống đĩa ngay sau khi encode, không tích lũy trong RAM
- **memmap** khi build FAISS: đọc file binary qua memory-mapped IO, không copy toàn bộ
- **Producer-consumer threading**: thread đọc file JSONL song song với GPU encode
- **Checkpoint/Resume**: lưu state mỗi 5,000 docs, tự tiếp tục nếu bị ngắt
- RAM thực tế tối đa: `batch_size × 4 × 768 × 4 bytes` ≈ **vài trăm MB**

### 2.5 Hard Geo-Filter sau FAISS

Vấn đề phát hiện: embedding của `"bình định"` và `"bình dương"` rất gần nhau trong vector space → FAISS trả về kết quả sai tỉnh.

Giải pháp: sau khi FAISS search, detect địa danh trong query → **hard-filter** theo field `Địa chỉ`:

```python
detected_geo = _detect_geo(query)   # "nhà hàng bình định" → "bình định"
if detected_geo:
    geo_filtered = [r for r in ranked
                    if detected_geo in norm(r.doc['Địa chỉ'])]
```

Áp dụng ở cả **Hybrid** (sau fusion) và **BM25/Vector** (trong app.py). Unicode NFC-normalised trước khi so sánh để tránh mismatch.

---

## 3. Hybrid Search

### 3.1 Công thức

```
Hybrid = 0.65 × BM25_normalised + 0.35 × Vector_normalised
```

BM25 score được normalize về [0, 100] theo max. Vector score đã ở [0, 100] (cosine × 100).

### 3.2 Quy trình

1. Fetch `top_k × 3` candidates từ cả BM25 và Vector (over-fetch để union đủ rộng)
2. Normalize BM25 → [0, 100]
3. Fuse: `0.65 × BM25 + 0.35 × Vector`
4. Apply hard geo-filter nếu query có địa danh
5. Sort, trả về top_k

### 3.3 Lý do trọng số 65/35

Dữ liệu doanh nghiệp Việt Nam có nhiều **tên riêng, mã số thuế, địa chỉ** → BM25 exact match rất quan trọng. Vector search bổ sung khả năng tìm ngữ nghĩa và đồng nghĩa. Trọng số 65/35 sau thực nghiệm cho kết quả tốt nhất.

---

## 4. Sản phẩm Web — Streamlit Interface (3đ)

### 4.1 Tính năng

| Tính năng | Chi tiết |
|---|---|
| **Search** | 3 phương pháp: BM25 / Vector / Hybrid, Enter hoặc nút bấm |
| **Filter** | Tình trạng, tỉnh/thành, ngành nghề — auto re-search khi thay đổi |
| **Pagination** | 10 kết quả/trang, điều hướng ◀ / ▶ |
| **Stats bar** | Tổng kết quả, sau bộ lọc, thời gian (ms), phương pháp |
| **Score badge** | Màu phân biệt BM25 (cam) / Vector (xanh lá) / Hybrid (xanh dương) |
| **Sub-scores** | Hybrid mode hiển thị BM25, Vector, Hybrid score từng kết quả |
| **Caching** | `@st.cache_resource` — index load 1 lần, tái dùng toàn session |

### 4.2 Smart Filter

Filter **tỉnh/thành** và **ngành nghề** không chỉ là post-filter mà còn được **incorporate vào query** để re-search:

```
user gõ filter "hà nội" → effective_query = "điện tử" + "hà nội"
→ re-search với query mới → kết quả địa lý chính xác
```

| Bộ lọc | Loại | Cơ chế |
|---|---|---|
| Tình trạng hoạt động | Post-filter | Lọc trên kết quả đã có |
| Tỉnh / Thành phố | Re-search trigger | Incorporate vào query + geo hard-filter |
| Ngành nghề | Re-search trigger | Incorporate vào query |

### 4.3 Geographic-Aware BM25

Phát hiện lỗi: query `"nhà hàng hà nội"` trả về kết quả TP HCM vì intent expansion `food_service` thêm 5 terms phụ, TP HCM có nhiều F&B hơn → dominate score.

Fix: khi query chứa tên tỉnh/thành, **tắt intent group expansion**:

```python
has_geo_term = any(t in city_phrase_set for t in base_terms)
if not has_geo_term:
    # expand food_service, technology, etc.
    for group_name in activated_groups:
        expanded_terms.extend(...)
```

Kết quả: `"nhà hàng hà nội"` → chỉ 2 terms `[nhà_hàng, hà_nội]`, địa lý không bị lấn át.

---

## 5. So sánh 3 phương pháp — Ví dụ thực tế

### 5.1 Query ngữ nghĩa: `"vận chuyển hàng hóa"`

| Phương pháp | Kết quả top-3 (ngành nghề) | Nhận xét |
|---|---|---|
| **BM25** | Vận tải đường bộ · Kho bãi · Giao nhận hàng hóa | Khớp chữ "vận chuyển" chính xác |
| **Vector** | Trung chuyển · Vận tải đường bộ · Xuất nhập khẩu | Tìm thêm đồng nghĩa tiếng Anh/tắt |
| **Hybrid** | Vận tải đường bộ · Kho bãi · Trung chuyển  | Kết hợp cả hai, recall cao nhất |

→ **Vector tốt hơn** khi query có từ đồng nghĩa hoặc từ tiếng Anh.

### 5.2 Query địa lý: `"nhà hàng hà nội"`

| Phương pháp | Địa chỉ kết quả | Nhận xét |
|---|---|---|
| **BM25** | Hà Nội ✓ | Exact match "hà_nội" trong inverted index |
| **Vector** | Hà Nội ✓ | Geo hard-filter loại kết quả sai tỉnh |
| **Hybrid** | Hà Nội ✓ | BM25 weight 65% + hard geo-filter |

→ **BM25 tốt hơn** cho query địa lý chính xác. Vector cần geo-filter mới đúng.

### 5.3 Query đơn lẻ: `"điện tử"`

| Phương pháp | Kết quả | Nhận xét |
|---|---|---|
| **BM25** | Linh kiện điện tử · Quang học · Thiết bị điện tử | Mở rộng ngữ nghĩa sang các ngành liên quan |
| **Vector** | Linh kiện điện tử | Khớp chính xác, rank tốt |
| **Hybrid** | Linh kiện điện tử · Quang học ·  Thiết bị điện tử | Cân bằng precision (BM25) và recall (Vector) |

→ **Hybrid tốt nhất** cho query ngắn vì kết hợp precision của BM25 và semantic coverage của Vector.

### 5.5 Query tiếng Anh: `"shipping logistics"`

| Phương pháp | Kết quả | Nhận xét |
|---|---|---|
| **BM25** | Các công ty có Shipping & Logistics trong tên và thông tin | Từ tiếng Anh không có trong inverted index -> khớp chính xác từ|
| **Vector** | Vận tải đường bộ · Kho vận · Giao nhận | Cross-lingual matching hoạt động tốt |
| **Hybrid** | Vận tải · Logistics | Kết hợp cả 2, ưu tiên kết quả từ BM25 vì trọng số lớn hơn |

→ **Vector tốt hơn hẳn** cho cross-lingual query. BM25 không index tiếng Anh.

---

## 6. Evaluation (2đ)

### 6.1 Bộ test

- **20 queries** tiếng Việt, cover đa ngành: công nghệ, F&B, xây dựng, logistics, y tế, giáo dục, năng lượng, thời trang, viễn thông, tài chính, dầu khí, nông nghiệp...
- **Relevance judgment**: tự động — doc là relevant nếu chứa ít nhất 1 keyword trong `Tên doanh nghiệp`, `Ngành nghề kinh doanh`, `Tên giao dịch`

### 6.2 Metrics

| Metric | Công thức |
|---|---|
| Precision@10 | `\|relevant ∩ top10\| / 10` |
| Recall@10 | `\|relevant ∩ top10\| / \|relevant\|` |
| MRR | `1 / rank(first_relevant_doc)` |

### 6.3 Kết quả so sánh

Chạy `python evaluation.py` trên 20 queries, pool 50 kết quả/method, đánh giá @k=10:

| Method | Precision@10 | Recall@10 | MRR | Avg time (ms) |
|--------|--------------|-----------|-----|---------------|
| BM25 | **0.930** | **0.131** | **0.960** | 305 |
| Vector | 0.720 | 0.081 | 0.761 | **91** |
| Hybrid | **0.930** | **0.131** | **0.960** | 410 |

> Relevance judgment: pooling — doc là relevant nếu chứa ≥1 keyword trong `Tên doanh nghiệp`, `Ngành nghề kinh doanh`, `Tên giao dịch`.

### 6.4 Phân tích

**Hybrid = BM25 trên bộ test này**

Số liệu Hybrid và BM25 giống nhau hoàn toàn. Nguyên nhân: với dataset doanh nghiệp Việt Nam (tên riêng, ngành nghề cụ thể), BM25 exact match đã có Precision@10 = 0.93, nên Vector (trọng số 35%) không đổi được thứ tự top-10. Hybrid vẫn có giá trị ở các trường hợp BM25 trả về ít kết quả (query tiếng Anh, query đồng nghĩa).

**Recall thấp (0.131) là hợp lý**

Có thể có hàng nghìn doc relevant trong 1.62M tài liệu; top-10 chỉ cover được ~13% — đúng bản chất short-list retrieval trên corpus lớn.

**Vector nhanh hơn nhưng precision thấp hơn**

Vector 91ms (FAISS IVFPQ, encode cố định) vs BM25 305ms (preprocessor + inverted index lookup). Tuy nhiên 20 queries trong bộ test chủ yếu là exact-match nên BM25 có lợi thế rõ ràng. Vector tốt hơn ở query ngữ nghĩa/tiếng Anh (`"shipping logistics"`) — thiểu số trong bộ test.

**BM25 tốt hơn Vector khi:**
- Query địa lý: `"nhà hàng hà nội"` — exact match token `hà_nội` mạnh hơn embedding similarity
- Tên tỉnh dễ nhầm: `"bình định"` vs `"bình dương"` — BM25 phân biệt hoàn hảo
- Query tên công ty cụ thể: exact string match hiệu quả hơn cosine similarity

**Vector tốt hơn BM25 khi:**
- Query tiếng Anh: `"shipping logistics"` → tìm được vận tải, kho vận
- Tên ngành đồng nghĩa: `"CNTT"` ↔ `"công nghệ thông tin"` ↔ `"phần mềm"`

---

## 7. Kiến trúc tổng thể

```
Query
  │
  ├─ TextPreprocessor.build_search_terms()
  │    ├─ Segment phrases: "nhà hàng" → nhà_hàng, "hà nội" → hà_nội
  │    ├─ Geographic-aware: có tỉnh/thành → tắt intent expansion
  │    └─ Intent group expansion: "nhà hàng" → thực_phẩm, ăn_uống, ...
  │
  ├─ BM25Ranker.rank_documents()
  │    ├─ Inverted index lookup (SPIMI-built, 404MB)
  │    └─ Score = Σ IDF(qi) × TF_normalised(qi, d)
  │
  ├─ VectorSearcher.search()
  │    ├─ Encode: "query: <text>" → 768-dim vector
  │    ├─ FAISS IVFPQ search → top candidates
  │    ├─ Multi-field grouping (MAX / full-doc-only tuỳ geo)
  │    ├─ Hard geo-filter (address exact match)
  │    └─ Cosine similarity → [0, 100]
  │
  └─ HybridSearch.search()
       ├─ Normalize BM25 → [0, 100]
       ├─ Fuse: 0.65 × BM25 + 0.35 × Vector
       ├─ Hard geo-filter sau fusion
       └─ Sort → top_k
              │
              └─ Streamlit UI
                   ├─ Smart Filter (re-search khi thay đổi)
                   └─ Pagination (10/page)
```

---

## 8. Hiệu năng hệ thống

| Thao tác | Thời gian |
|---|---|
| BM25 search (top 50) | ~ 300ms |
| Vector search (top 50, IVFPQ) | ~50ms |
| Hybrid search (top 50) | ~60ms |
| Build BM25 index (1.62M docs) | ~10–15 phút |
| Build Vector index (GPU RTX 3050, 4 fields) | ~5 giờ |
| Load hệ thống lần đầu (web) | ~5 giây |
| Load lần sau (cached) | < 1ms |

| Component | Dung lượng |
|---|---|
| Inverted index (BM25) | 404 MB |
| FAISS IVFPQ index (1.62M × 4 fields) | 261 MB |
| `idx_offsets.npy` | 12.3 MB |

---

## 9. Hướng dẫn chạy

```bash
# Build BM25 index
python -m src.indexer.index_builder data_sample/final_merged_3v6.jsonl

# Build Vector index (GPU)
python -m src.indexer.build_vector_index data_sample/final_merged_3v6.jsonl --device cuda

# Chạy Web Interface
streamlit run src/ui/app.py
# → http://localhost:8501

# Chạy Evaluation
python evaluation.py
```

---

## 10. AI Usage Log

Toàn bộ tương tác với AI trong quá trình phát triển được ghi tại `ai_log.md`.
Mỗi entry ghi rõ: ngày, task, prompt gốc, phản hồi AI, quyết định cuối của nhóm.

---

**Team UnderFitting** · SEG301 · 2026
