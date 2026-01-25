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
│   ├── indexer/            # Milestone 2: Index construction
│   │
│   ├── ranking/            # Milestone 2 & 3: Ranking algorithms
│   │
│   └── ui/                 # Milestone 3: User Interface
│
└── tests/                  # (Recommended) Unit tests for core algorithms

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

## 8. 🤖 AI Usage & Transparency

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

## 9. 📝 Notes

The full dataset is not included in this repository due to size limitations

JSONL format is used for efficient streaming and large-scale processing

The project is structured to support incremental development across milestones

---
**Team UnderFitting**
