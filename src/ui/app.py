"""Streamlit Web Interface for the Hybrid Search System."""

import sys
import logging
import time
from pathlib import Path
from typing import Optional

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indexer.storage import InvertedIndexStorage
from src.indexer.doc_store import DocStore
from src.indexer.preprocessor import TextPreprocessor
from src.ranking.bm25_ranker import BM25Ranker
from src.ranking.vector_searcher import VectorSearcher
from src.ranking.hybrid_search import HybridSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 10

# ===================================
# Page config
# ===================================

st.set_page_config(
    page_title="Vietnamese Company Search",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Global ── */
    [data-testid="stAppViewContainer"] {
        background: #0f1117;
    }
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] div {
        color: #e2e8f0;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #1a1f2e;
    }
    [data-testid="stSidebar"] * {
        color: #e8eaf0 !important;
    }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stSlider label {
        color: #b0b8cc !important;
        font-size: 0.85rem;
    }

    /* ── Search button ── */
    div.stButton > button {
        background: #2563eb;
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 10px 28px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
        width: 100%;
    }
    div.stButton > button:hover {
        background: #1d4ed8;
    }

    /* ── Result card ── */
    .result-card {
        background: #1e2330;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        border-left: 5px solid #3b82f6;
        transition: box-shadow 0.2s;
    }
    .result-card:hover {
        box-shadow: 0 4px 20px rgba(59,130,246,0.2);
    }
    .result-rank {
        font-size: 0.78rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .result-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 12px;
    }
    .result-field {
        font-size: 0.875rem;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .result-field span {
        font-weight: 600;
        color: #cbd5e1;
    }

    /* ── Score badge ── */
    .score-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }
    .bm25-badge   { background: #fff3e0; color: #e65100 !important; border: 1.5px solid #ffb74d; }
    .vector-badge { background: #e8f5e9; color: #2e7d32 !important; border: 1.5px solid #81c784; }
    .hybrid-badge { background: #e3f2fd; color: #1565c0 !important; border: 1.5px solid #64b5f6; }

    /* ── Sub-score row ── */
    .sub-scores {
        display: flex;
        gap: 8px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    .sub-score-pill {
        background: #0f1117;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 500;
    }

    /* ── Status pill ── */
    .status-active   { color: #4ade80; font-weight: 600; }
    .status-inactive { color: #f87171; font-weight: 600; }

    /* ── Method tag in info bar ── */
    .method-tag {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        border-radius: 8px;
        padding: 2px 10px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* ── Text input ── */
    div[data-testid="stTextInput"] input {
        background: #1e2330 !important;
        color: #f1f5f9 !important;
        border: 2px solid #334155 !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #3b82f6 !important;
    }
    div[data-testid="stTextInput"] input::placeholder {
        color: #64748b !important;
    }

    /* ── Metrics ── */
    [data-testid="metric-container"] {
        background: #1e2330;
        border-radius: 12px;
        padding: 14px 20px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.3);
    }

    /* hide default form border */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }

    /* ── Pagination ── */
    .pagination-info {
        text-align: center;
        color: #94a3b8;
        font-size: 0.92rem;
        padding: 6px 0;
        font-weight: 500;
    }
    .filter-section-title {
        font-size: 0.8rem;
        font-weight: 700;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 4px;
    }
    .filter-badge {
        display: inline-block;
        background: #1e3a5f;
        color: #93c5fd !important;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 2px 3px;
    }
</style>
""", unsafe_allow_html=True)


# ===================================
# Cached loaders
# ===================================

@st.cache_resource
def load_bm25_system():
    index_dir = str(PROJECT_ROOT / 'inverted_index')
    storage = InvertedIndexStorage(index_dir=index_dir)
    inverted_index, doc_lengths, doc_offsets, jsonl_path = storage.load_final_index()
    doc_store    = DocStore(jsonl_path, doc_offsets)
    bm25_ranker  = BM25Ranker(inverted_index, doc_lengths, doc_store)
    preprocessor = TextPreprocessor()
    logger.info(f"BM25 ready — {len(doc_lengths):,} docs")
    return bm25_ranker, preprocessor, doc_store


@st.cache_resource
def load_vector_system():
    index_dir = str(PROJECT_ROOT / 'vector_index')
    searcher = VectorSearcher(index_dir=index_dir)
    logger.info("Vector Search ready")
    return searcher


@st.cache_resource
def load_all_systems():
    """Load BM25 + Vector + Hybrid all at once on startup."""
    bm25_ranker, preprocessor, doc_store = load_bm25_system()

    vector_searcher: Optional[VectorSearcher] = None
    hybrid: Optional[HybridSearch] = None
    try:
        vector_searcher = load_vector_system()
        hybrid = HybridSearch(
            bm25_ranker=bm25_ranker,
            vector_searcher=vector_searcher,
            preprocessor=preprocessor,
            bm25_weight=0.65,
            vector_weight=0.35,
        )
    except Exception as exc:
        logger.warning(f"Vector Search not available: {exc}")

    return {
        'bm25': bm25_ranker,
        'preprocessor': preprocessor,
        'vector': vector_searcher,
        'hybrid': hybrid,
    }


# ===================================
# Helpers
# ===================================

def _status_html(status: str) -> str:
    cls = 'status-active' if 'đang hoạt động' in status.lower() else 'status-inactive'
    return f"<span class='{cls}'>{status}</span>"


def _render_result(rank: int, doc_id: int, score: float, doc: dict,
                   badge_cls: str, show_sub: bool) -> None:
    name    = doc.get('Tên doanh nghiệp', 'N/A')
    tax_id  = doc.get('Mã số thuế', 'N/A')
    industry = doc.get('Ngành nghề kinh doanh', 'N/A')
    address  = doc.get('Địa chỉ', 'N/A')
    status   = doc.get('Tình trạng hoạt động', 'N/A')

    sub_html = ''
    if show_sub and '_hybrid_scores' in doc:
        bd = doc['_hybrid_scores']
        sub_html = (
            '<div class="sub-scores">'
            f'<span class="sub-score-pill">BM25: {bd["bm25"]:.1f}</span>'
            f'<span class="sub-score-pill">Vector: {bd["vector"]:.1f}</span>'
            f'<span class="sub-score-pill">Hybrid: {bd["hybrid"]:.1f}</span>'
            '</div>'
        )

    st.markdown(f"""
    <div class="result-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div style="flex:1; min-width:0;">
                <div class="result-rank">#{rank}</div>
                <div class="result-name">{name}</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px 24px;">
                    <div class="result-field"><span>Mã số thuế:</span> {tax_id}</div>
                    <div class="result-field"><span>Địa chỉ:</span> {address}</div>
                    <div class="result-field"><span>Ngành nghề:</span> {industry}</div>
                    <div class="result-field"><span>Trạng thái:</span> {_status_html(status)}</div>
                </div>
                {sub_html}
            </div>
            <div style="margin-left:16px; flex-shrink:0;">
                <span class="score-badge {badge_cls}">Score: {score:.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _apply_filters(results: list, status_filter: str,
                   province_filter: str, industry_filter: str) -> list:
    """Filter results by status, province, and industry (case-insensitive substring)."""
    filtered = []
    for item in results:
        _, _, doc = item
        status   = doc.get('Tình trạng hoạt động', '')
        address  = doc.get('Địa chỉ', '')
        industry = doc.get('Ngành nghề kinh doanh', '')

        if status_filter == "Đang hoạt động" and 'đang hoạt động' not in status.lower():
            continue
        if status_filter == "Ngừng hoạt động" and 'đang hoạt động' in status.lower():
            continue
        if province_filter and province_filter.lower() not in address.lower():
            continue
        if industry_filter and industry_filter.lower() not in industry.lower():
            continue

        filtered.append(item)
    return filtered


def _render_pagination(current_page: int, total_pages: int) -> None:
    """Render pagination controls; updates st.session_state['page'] and reruns."""
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col_prev, col_info, col_next = st.columns([1, 3, 1])

    with col_prev:
        if st.button("◀ Trước", disabled=(current_page <= 1), key="btn_prev"):
            st.session_state['page'] = current_page - 1
            st.rerun()

    with col_info:
        st.markdown(
            f"<div class='pagination-info'>Trang {current_page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button("Tiếp ▶", disabled=(current_page >= total_pages), key="btn_next"):
            st.session_state['page'] = current_page + 1
            st.rerun()


# ===================================
# Main app
# ===================================

def main():
    # ── Sidebar ──────────────────────────────
    with st.sidebar:
        st.markdown("## ✏️ Tùy chọn")
        search_method = st.radio(
            "Phương pháp tìm kiếm",
            ["BM25 Search", "Vector Search", "Hybrid Search"],
            index=2,
        )
        top_k = st.slider("Tổng số kết quả tìm kiếm", 10, 200, 50)

        st.markdown("---")
        st.markdown("<div class='filter-section-title'>🔽 Bộ lọc kết quả</div>",
                    unsafe_allow_html=True)

        status_filter = st.selectbox(
            "Tình trạng hoạt động",
            ["Tất cả", "Đang hoạt động", "Ngừng hoạt động"],
            key="filter_status",
        )
        province_filter = st.text_input(
            "Tỉnh / Thành phố",
            placeholder="VD: Hà Nội, TP.HCM, Đà Nẵng",
            key="filter_province",
        )
        industry_filter = st.text_input(
            "Ngành nghề",
            placeholder="VD: công nghệ, xây dựng, dệt may",
            key="filter_industry",
        )

        st.markdown("---")
        st.markdown(
            "<small style='color:#6b7280'>**Team UnderFitting** · SEG301<br>"
            "BM25 + Vector + Hybrid</small>",
            unsafe_allow_html=True,
        )

    # ── Header ───────────────────────────────
    st.markdown(
        "<h1 style='margin-bottom:4px'>🏢 Vietnamese Company Search</h1>"
        "<p style='color:#6b7280; margin-top:0'>Tìm kiếm thông tin doanh nghiệp Việt Nam</p>",
        unsafe_allow_html=True,
    )

    # ── Preload all systems ───────────────────
    with st.spinner("⏳ Đang tải hệ thống tìm kiếm…"):
        try:
            system = load_all_systems()
        except Exception as exc:
            logger.error(f"System load failed: {exc}")
            system = None

    if system is None:
        st.error("❌ Không tải được index BM25. Hãy build index trước.")
        st.code("python -m src.indexer.index_builder data_sample/sample_cleaned.jsonl")
        return

    if search_method == "Vector Search" and system['vector'] is None:
        st.warning("⚠️ Vector index chưa sẵn sàng — chuyển sang BM25.")
        search_method = "BM25 Search"
    if search_method == "Hybrid Search" and system['hybrid'] is None:
        st.warning("⚠️ Vector index chưa sẵn sàng — chuyển sang BM25.")
        search_method = "BM25 Search"

    # ── Search bar (form → Enter triggers search) ──
    with st.form("search_form", clear_on_submit=False):
        col1, col2 = st.columns([5, 1])
        with col1:
            query = st.text_input(
                "query",
                placeholder="Nhập tên công ty, ngành nghề, địa chỉ…",
                label_visibility="collapsed",
            )
        with col2:
            search_btn = st.form_submit_button("🔍 Tìm kiếm", use_container_width=True)

    # ── Trigger new search on submit ─────────
    if search_btn and query:
        t0 = time.time()
        try:
            if search_method == "BM25 Search":
                query_terms, _ = system['preprocessor'].build_search_terms(query)
                results = system['bm25'].rank_documents(query_terms=query_terms, top_k=top_k)
                badge_cls = 'bm25-badge'
                method_label = '📝 BM25'
            elif search_method == "Vector Search":
                results = system['vector'].search(query, top_k=top_k)
                badge_cls = 'vector-badge'
                method_label = '🤖 Vector'
            else:
                results = system['hybrid'].search(query, top_k=top_k, return_details=True)
                badge_cls = 'hybrid-badge'
                method_label = '⚡ Hybrid'
        except Exception as exc:
            st.error(f"❌ Lỗi tìm kiếm: {exc}")
            logger.exception("Search error")
            return

        elapsed_ms = (time.time() - t0) * 1000
        st.session_state.update({
            'results': results,
            'last_query': query,
            'badge_cls': badge_cls,
            'method_label': method_label,
            'elapsed_ms': elapsed_ms,
            'page': 1,
        })

    # ── Nothing to show yet ───────────────────
    if 'results' not in st.session_state:
        return

    # ── Apply filters ─────────────────────────
    # Reset page to 1 when filter values change
    filter_key = f"{status_filter}|{province_filter}|{industry_filter}"
    if st.session_state.get('_filter_key') != filter_key:
        st.session_state['_filter_key'] = filter_key
        st.session_state['page'] = 1

    all_results     = st.session_state['results']
    filtered_results = _apply_filters(all_results, status_filter, province_filter, industry_filter)

    badge_cls    = st.session_state['badge_cls']
    method_label = st.session_state['method_label']
    elapsed_ms   = st.session_state['elapsed_ms']
    last_query   = st.session_state['last_query']

    # ── Stats bar ────────────────────────────
    active_filters = [f for f in [
        (status_filter != "Tất cả", status_filter),
        (bool(province_filter), province_filter),
        (bool(industry_filter), industry_filter),
    ] if f[0]]

    filter_tag_html = ''.join(
        f"<span class='filter-badge'>{v}</span>" for _, v in active_filters
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng kết quả", len(all_results))
    c2.metric("Sau bộ lọc", len(filtered_results))
    c3.metric("Thời gian (ms)", f"{elapsed_ms:.1f}")
    c4.metric("Phương pháp", method_label)

    filter_note = (
        f" &nbsp;|&nbsp; Bộ lọc: {filter_tag_html}" if active_filters else ""
    )
    st.markdown(
        f"<div style='margin:12px 0 8px;color:#6b7280;font-size:0.9rem'>"
        f"Hiển thị <b>{len(filtered_results)}</b> / <b>{len(all_results)}</b> kết quả cho "
        f"<span class='method-tag' style='color:#000'>{method_label}</span>"
        f" &nbsp;—&nbsp; <i>\"{last_query}\"</i>"
        f"{filter_note}</div>",
        unsafe_allow_html=True,
    )

    if not filtered_results:
        st.info("Không có kết quả nào khớp với bộ lọc hiện tại.")
        return

    # ── Pagination logic ──────────────────────
    total_items  = len(filtered_results)
    total_pages  = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    current_page = int(st.session_state.get('page', 1))
    current_page = max(1, min(current_page, total_pages))
    st.session_state['page'] = current_page

    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx   = min(start_idx + ITEMS_PER_PAGE, total_items)
    page_results = filtered_results[start_idx:end_idx]

    # ── Results ──────────────────────────────
    show_sub = (st.session_state.get('method_label', '') == '⚡ Hybrid')
    for rank, (doc_id, score, doc) in enumerate(page_results, start_idx + 1):
        _render_result(rank, doc_id, score, doc, badge_cls, show_sub)

    # ── Pagination controls ───────────────────
    if total_pages > 1:
        _render_pagination(current_page, total_pages)


if __name__ == "__main__":
    main()
