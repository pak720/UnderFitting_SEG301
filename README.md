# UnderFitting_SEG301
SEG301 - SEARCH ENGINES & INFORMATION RETRIEVAL


# SEG301 Project – Group UnderFitting

## 📁 Project Structure

```text
SEG301-Project-GroupX/
│── .gitignore              # Git ignore config (venv, large data, __pycache__)
│── README.md               # Project setup, run instructions & Full Dataset link
│── ai_log.md               # AI usage log (updated daily)
│── requirements.txt        # Required Python libraries (pip freeze > requirements.txt)
│
├── docs/                   # Reports & documentation
│   ├── Milestone1_Report.pdf
│   ├── Milestone2_Report.pdf
│   └── Milestone3_Presentation.pdf
│
├── data_sample/            # 100–500 sample docs for testing (DO NOT upload 1M docs)
│   └── sample.jsonl
│
├── src/                    # Main source code
│   ├── __init__.py
│   │
│   ├── crawler/            # Milestone 1: Data collection
│   │   ├── spider.py       # Core crawling logic
│   │   ├── parser.py       # HTML processing & tokenization
│   │   └── utils.py        # Helpers (proxy, user-agent)
│   │
│   ├── indexer/            # Milestone 2: Index construction
│   │   ├── spimi.py        # SPIMI algorithm
│   │   ├── merging.py     # Block merging logic
│   │   └── compression.py # Index compression (optional)
│   │
│   ├── ranking/            # Milestone 2 & 3: Ranking algorithms
│   │   ├── bm25.py         # BM25 (implemented from scratch)
│   │   └── vector.py      # Semantic search (library-based for M3)
│   │
│   └── ui/                 # Milestone 3: User Interface
│       └── app.py          # Streamlit / Flask application
│
└── tests/                  # (Recommended) Unit tests for core algorithms
    ├── test_spimi.py
    └── test_bm25.py


