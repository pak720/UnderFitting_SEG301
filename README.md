# UnderFitting_SEG301
SEG301 - SEARCH ENGINES & INFORMATION RETRIEVAL

## 1. 📊 Project Overview

This project implements a **Vertical Search Engine** from scratch, following the core principles of Information Retrieval (IR).  
The system is designed to handle **large-scale data (≥ 1 million documents)** and supports both **traditional IR** and **modern AI-based search**.

The project focuses on building a complete pipeline:
> Crawling → Data Cleaning → Indexing → Ranking → Search Interface

---

## 2. 🎯 Project Objectives

- Build a vertical search engine without relying on pre-built IR frameworks
- Process and manage large-scale real-world data
- Implement classical IR algorithms (SPIMI, BM25)
- Extend the system with semantic search using vector embeddings

---

## 3. 🚀 Team - Group UnderFitting

| Name | ID |
|----------|----------|
| Võ Minh Huy | QE190059 |
| Thân Phúc Hậu | QE190002  |
| Nguyễn Lê Anh Duy | QE190134  |

## 4. 📈 Dataset Description

- **Domain**: Vietnamese company information and employee reviews
- **Scale**: 1,620,401 documents
- **Storage format**: `JSONL` (one JSON object per line)
- **Characteristics**:
  - Structured company metadata
  - Optional nested reviews per company
  - Cleaned, normalized, and deduplicated
  - Optimized for streaming and large-scale indexing

Due to storage limitations, the **full dataset is not included** in this repository.  
A small subset is provided in `data_sample/sample.jsonl` for testing and demonstration purposes.

---

## 5. 📁 Project Structure

```text
UnderFitting_SEG301/
│── .gitignore              # Git ignore config (venv, large data, __pycache__)
│── README.md               # Project setup, run instructions & Full Dataset link
│── ai_log.md               # AI usage log (updated daily)
│── requirements.txt        # Required Python libraries (pip freeze > requirements.txt)
│
├── docs/                   # Reports & documentation
│   ├── Milestone 1 Report.pdf
│   ├── Milestone 2 Report.pdf
│   └── Milestone 3 Presentation.pdf
│
├── data_sample/            
│   └── sample.jsonl        # 100–500 sample docs for testing
│   └── Full_File_Links.md  # Link to drive containing full dataset
│
├── src/                    # Main source code
│   ├── __init__.py
│   │
│   ├── crawler/            # Milestone 1: Data collection
│   │   ├── spider.py       # Core crawling logic
│   │   ├── parser.py       # HTML processing & tokenization
│   │   └── utils.py        # Helpers (proxy, user-agent)
│   │   └── CareerLink.py   # Code crawling CareerLink.vn
│   │   └── Craw_thongtincongty.py   # Code crawling thongtincongty.vn
│   │   └── Crawling_tratencongty.py   # Code crawling tratencongty.com
│   │   └── Crawling_infodoanhnghiep.py     # Code crawling infodoanhnghiep.py
│   │   └── MERGE9000.py     # Code merging reviews with data - thredshold 0.83
│   │   └── company_with_reviews.py     # Code merging reviews with data - thredshold 0.9
│   │   └── Preprocessing.ipynb     # Code preprocessing data - check duplicate, remove duplicate, merge json...   
│   │
│   ├── indexer/            # Milestone 2 & 3: Index construction
│   |   ├── __init__.py                 # Package initialization
│   |   ├── __main__.py                 # Entry point for running as module
│   |   ├── preprocessor.py             # Text preprocessing & tokenization
│   |   ├── storage.py                  # Inverted index storage management
│   |   ├── spimi_indexer.py            # SPIMI algorithm implementation
│   |   ├── console_app.py              # Interactive console application
│   |   ├── index_builder.py            # BM25 index building script
│   |   ├── vector_indexer.py           # NEW: Vector index builder (GPU, resume)
│   |   └── build_vector_index.py       # NEW: CLI entry point for vector indexer
│   │
│   ├── ranking/            # Milestone 2 & 3: Ranking algorithms
|   |   ├── __init__.py                 # Package initialization
|   |   ├── bm25_ranker.py              # BM25 ranking algorithm
|   |   ├── vector_searcher.py          # NEW: Semantic search with FAISS
|   |   └── hybrid_search.py            # NEW: Hybrid BM25 + Vector ranking
│   │
│   └── ui/                 # Milestone 3: User Interface
│       └── app.py                      # NEW: Streamlit web interface
│
├── evaluation.py                       # NEW: Evaluation framework (Precision, Recall, MRR)
└── tests/                              # (Recommended) Unit tests for core algorithms

```
Each component is designed to be independent but composable, allowing the system to scale and evolve across milestones.

## 6. 🛠️ Environment Setup

### 6.1 Requirements

- **Python**: `>= 3.10`
- **Recommended OS**: Linux / Windows / Google Colab
- **GPU**: Optional (used for semantic embedding and vector search)

### 6.2 Install Dependencies

```bash
pip install -r requirements.txt
```

## 7. 🗒️ How to Run (Basic)

The following examples demonstrate how to run the crawler and preprocessing scripts **based on the current files available in this repository**.

### Run website-specific crawlers

Crawl company information and reviews from different data sources:

```bash
python Crawl_thongtincongty.py
```
```bash
python CareerLink.py
```
```bash
python Crawling_tratencongty.py
```

### Run data preprocessing and merging

After crawling, clean and merge the collected data:

```bash
python MERGE9000.py
```
or
```bash
python company_with_reviews.py
```
Alternatively, interactive preprocessing and debugging can be performed using:
```bash
Preprocessing.ipynb
```
> Note:
> Scripts are designed to be executed independently.
> Output paths and parameters can be adjusted directly inside each script.
> The execution order typically follows: crawl → preprocess → merge.

---

## 8. 🔍 Search Index Building & Ranking

### Search System – SPIMI Indexing + BM25 Ranking

This search system is built using:

- **SPIMI (Single-Pass In-Memory Indexing)** for inverted index construction  
- **BM25** for document ranking  

---

## 🚀 How to Use

### 1️⃣ Build the Index

First, build the inverted index from a JSONL file:

```bash
# Using sample file (from project root)
python -m src.indexer.index_builder data_sample/sample_cleaned.jsonl

# Specify output directory
python -m src.indexer.index_builder data_sample/sample_cleaned.jsonl --index-dir inverted_index

# Specify memory limit (default: 500 MB)
python -m src.indexer.index_builder data_sample/sample_cleaned.jsonl --memory 800
```

**Output:**
- The system creates an ```inverted_index/``` folder containing:
  - `postings.bin` - Binary index postings
  - `terms.pkl` - Term mappings
  - `doc_info.pkl` - Document information
  - `metadata.json` - Index metadata

##### 2. Run the Search Console

After building the index:

```bash
python -m src.indexer
# or
python src/ranking/console_app.py
```

##### 3. Available Commands

Inside the console:

```
search <query>              - Search documents by industry/business type
  Example: search technology company

search2 <industry> <city>   - Search by industry AND city (auto-detect city)
  Example: search2 nhà hàng hà nội
           search2 dệt may hải phòng --top 15

search <query> --top N      - Return top N results (max 100)
  Example: search technology company --top 20

explain <query> [index]     - Explain BM25 score for result
  Example: explain technology company 0

help                        - Show help and available commands
exit                        - Exit application
```

##### 4. New Feature: Search by Industry + City (search2)

**Purpose:**  
Find companies by combining **industry/business type** and **geographic location** for precise results.

**Algorithm:**
1. Extract industry keywords from the query
2. Automatically detect city/province name (from 63 Vietnamese provinces/cities)
3. Search in Industry field for industry keywords
4. Filter results by city extracted from Address field
5. Return combined results with location information

**Syntax:**
```bash
search2 <industry_keyword> <city_name> [--top N]
```

**Examples:**

```bash
# Find restaurants in Hanoi
search2 nhà hàng hà nội

# Find textile companies in Hai Phong (top 15 results)
search2 dệt may hải phòng --top 15

# Find technology companies in Ho Chi Minh City
search2 công ty công nghệ tp hcm

# Find pharmacies in Thai Nguyen
search2 nhà thuốc thái nguyên

# Find food/beverage businesses in Da Nang
search2 thực phẩm đà nẵng --top 20
```

**Supported Cities (63 Vietnamese Provinces & Cities):**

Major Cities:
- Hà Nội, Hồ Chí Minh, Đà Nẵng, Hải Phòng, Cần Thơ

Northern Region:
- Thái Nguyên, Tuyên Quang, Sơn La, Bắc Ninh, Phú Thọ, Yên Bái, Hòa Bình, Lạng Sơn, Cao Bằng, Quảng Ninh, Điện Biên, Lai Châu, Hà Giang

North Central:
- Thanh Hóa, Nghệ An, Hà Tĩnh, Quảng Bình, Quảng Trị

Central:
- Thừa Thiên Huế, Quảng Nam, Quảng Ngãi, Bình Định, Phú Yên

South Central:
- Khánh Hòa, Ninh Thuận, Bình Thuận

Southeast:
- Long An, Đồng Tháp, An Giang, Kiên Giang, Cà Mau, Bến Tre, Trà Vinh, Vĩnh Long, Tiền Giang, Bình Dương, Bình Phước, Đồng Nai, Tây Ninh

Highlands:
- Lâm Đồng, Đắk Lắk, Đắk Nông

**Output Example:**

```
➤ search2 nhà hàng hà nội

🔍 Searching by Industry + City
   Industry: nhà hàng
   City: hà nội
────────────────────────────────────────
Industry query terms: nhà hàng
────────────────────────────────────────

Found 5 results in 23.45ms

📄 Rank 1
   Score: 8.2341
   Company: Nhà Hàng ABC
   Tax ID: 0123456789
   Industry: Dịch vụ ăn uống khác
   City: hà nội
   Address: 123 Tran Hung Dao, Quan Hoan Kiem, Ha Noi
   Status: Active

📄 Rank 2
   Score: 7.8956
   Company: Quán Ăn XYZ
   ...
```

**Key Features:**
- ✅ Automatic city detection from query (no need for separate parameters)
- ✅ Filters by Address field for geographic accuracy
- ✅ Supports all 63 Vietnamese provinces and cities
- ✅ Case-insensitive and accent-normalized
- ✅ Optional `--top N` limit (default: 10 results, max: 100)

**Difference between `search` and `search2`:**

| Feature | search | search2 |
|---------|--------|---------|
| Search by industry | ✅ | ✅ |
| Filter by city | ❌ | ✅ |
| City auto-detection | N/A | ✅ |
| Address field | Display only | Filter results |
| Use case | General industry search | Location-aware search |

---

##### SPIMI Indexing (Single-Pass In-Memory Indexing)

**Process:**
1. Read documents from JSONL
2. Text preprocessing (normalization, tokenization, stopword removal)
3. Compute term frequency per document
4. Build in-memory inverted index
5. When memory limit is exceeded → write block to disk
6. Merge all blocks into final inverted index

**Memory limit (default):**
```
memory_limit_mb = 500
```

##### BM25 Ranking Algorithm

**BM25 Formula:**
```
Score(q, d) = Σ IDF(qi) * (f(qi, d) * (k1 + 1)) / (f(qi, d) + k1 * (1 - b + b * |d|/avgdl))
```

Where:
- `f(qi, d)` = Term frequency (TF)
- `IDF(qi)` = log((N - n + 0.5) / (n + 0.5))
- `k1` = 1.5 (saturation parameter)
- `b` = 0.75 (length normalization parameter)
- `|d|` = Document length
- `avgdl` = Average document length

**Implementation notes:**
- ✅ No external ranking libraries used
- ✅ IDF values are cached
- ✅ Supports detailed score explanation

#### 🔍 Example Usage

##### Example 1: Search
```
➤ search technology company
🔍 Searching for: technology company
Query terms: technology, company
────────────────────────────────────────
Found 10 results in 45.23ms

📄 Rank 1
   Score: 12.4521
   Company: ABC Technology Co., Ltd
   Tax ID: 0123456789
   Industry: Technology Services
   Address: Ho Chi Minh City
   Status: Active
```

##### Example 2: Explain Ranking
```
➤ explain technology company 0
📊 Score Explanation for Result #1
   Company: ABC Technology Co., Ltd
   Total Score: 12.4521
────────────────────────────────────────
Document Length: 45 tokens
Average Document Length: 38.25 tokens

Term Contributions:
  technology:
    - Score: 4.2301
    - IDF: 2.1456
    - TF: 3
```

#### 📄 Dataset Format

Input file: `data_sample/sample_cleaned.jsonl`

Format JSONL:
```json
{"Tên doanh nghiệp": "...", "Mã số thuế": "...", "Địa chỉ": "...", ...}
{"Tên doanh nghiệp": "...", "Mã số thuế": "...", "Địa chỉ": "...", ...}
```

#### 🎓 Performance (Reference)
- Index building: ~100–200K documents/minute
- Search latency: < 100ms (top 10 results)
- Memory usage: ~500MB per block (configurable)

---

---

## 9. 🧠 Milestone 3: Vector Search & Web Interface

This milestone extends the search engine with semantic search capabilities and a web UI.

### New Components

| Component | Description |
|-----------|-------------|
| `src/indexer/vector_indexer.py` | Builds FAISS vector index from JSONL using Sentence-Transformers (GPU, producer-consumer pipeline, resume) |
| `src/ranking/vector_searcher.py` | Semantic search over FAISS index |
| `src/ranking/hybrid_search.py` | Combines BM25 + Vector search with configurable weights |
| `src/ui/app.py` | Streamlit web interface with BM25 / Vector / Hybrid modes |
| `evaluation.py` | Evaluation framework (Precision@10, Recall@10, MRR) |

---

### Step 1: Build BM25 Index (if not done)

```bash
python -m src.scripts.index_builder data_sample/sample_cleaned.jsonl
```

### Step 2: Build Vector Index

```bash
# Basic (auto-detects GPU)
python -m src.scripts.build_vector_index data_sample/final_merged_3v6.jsonl

# Specify output directory
python -m src.scripts.build_vector_index data_sample/final_merged_3v6.jsonl --index-dir vector_index

# Force GPU + FP16 for ~2x speed
python -m src.scripts.build_vector_index data_sample/final_merged_3v6.jsonl --device cuda --fp16

# Limit documents (for testing)
python -m src.scripts.build_vector_index data_sample/final_merged_3v6.jsonl --max-docs 1000

# Rebuild from scratch (ignore checkpoint)
python -m src.scripts.build_vector_index data_sample/final_merged_3v6.jsonl --no-resume
```

> **Resume:** If the process is interrupted (Ctrl+C), it saves a checkpoint automatically.
> Simply run the same command again — it will resume from where it stopped.

**Output files in `vector_index/`:**
- `vector.index` — FAISS index
- `id_to_doc.pkl` — Document mapping
- `metadata.json` — Index metadata

### Step 3: Run Web Interface

```bash
streamlit run src/ui/app.py
```

Then visit: `http://localhost:8501`

**Features:**
- ✅ BM25 Search (keyword-based)
- ✅ Vector Search (semantic)
- ✅ Hybrid Search (BM25 + Vector combined)
- ✅ Score breakdown and result visualization

### Step 4: Run Evaluation

```bash
python evaluation.py
```

**Output:** `evaluation_results.csv`, `evaluation_summary.json`, `EVALUATION_REPORT.md`

### Architecture

```
Query
  ├─→ BM25 Ranking        → Score normalization (0–100)
  ├─→ Vector Search       → L2 distance → similarity (0–100)
  └─→ Score Fusion        → Hybrid = 0.5 × BM25 + 0.5 × Vector
```

### Performance (Full Dataset — 1.62M docs)

| Stage | Details |
|-------|---------|
| Embedding (GPU RTX 3050) | ~56 docs/s, ~8 hours total |
| FAISS search latency | ~50ms per query |
| Hybrid search latency | ~60ms per query |

---

## 10. 🤖 AI Usage & Transparency

AI tools (e.g., ChatGPT) were used only as coding and reasoning assistants during the development process.

All AI interactions are documented in:
```bash
ai_log.md
```
Each log entry includes:
- User prompt
- AI response
- Context of usage

This ensures transparency and compliance with academic integrity requirements.

---

## 11. 📝 Notes

The full dataset is not included in this repository due to size limitations

JSONL format is used for efficient streaming and large-scale processing

The project is structured to support incremental development across milestones

---
**Team UnderFitting**
