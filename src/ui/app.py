"""
Streamlit Web Interface for Hybrid Search System
"""

import sys
import streamlit as st
import pandas as pd
import pickle
import logging
import json
from pathlib import Path
from typing import List, Dict, Tuple, Any
import time

# Ensure project root is in sys.path regardless of how Streamlit is launched
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indexer.storage import InvertedIndexStorage
from src.ranking.bm25_ranker import BM25Ranker
from src.ranking.vector_searcher import VectorSearcher
from src.ranking.hybrid_search import HybridSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================================
# Page Configuration
# ===================================

st.set_page_config(
    page_title="Vietnamese Company Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .result-card {
        background-color: #f0f2f6;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
    .score-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 5px;
        margin: 3px;
        font-weight: bold;
    }
    .bm25-badge { background-color: #ff7f0e; color: white; }
    .vector-badge { background-color: #2ca02c; color: white; }
    .hybrid-badge { background-color: #d62728; color: white; }
</style>
""", unsafe_allow_html=True)

# ===================================
# Initialize Session State
# ===================================

@st.cache_resource
def load_search_system():
    """Load search engines."""
    try:
        # Load BM25
        inverted_index_dir = str(PROJECT_ROOT / 'inverted_index')
        vector_index_dir = str(PROJECT_ROOT / 'vector_index')

        storage = InvertedIndexStorage(
            index_dir=inverted_index_dir
        )
        inverted_index, doc_info = storage.load_final_index()

        bm25_ranker = BM25Ranker(inverted_index, doc_info)
        logger.info("✓ BM25 loaded successfully")

        # Load Vector Search
        try:
            vector_searcher = VectorSearcher(index_dir=vector_index_dir)
            logger.info("✓ Vector Search loaded successfully")
        except Exception as e:
            logger.warning(f"Vector Search not available: {str(e)}")
            vector_searcher = None

        # Create Hybrid Search
        if vector_searcher:
            hybrid_search = HybridSearch(
                bm25_ranker=bm25_ranker,
                vector_searcher=vector_searcher,
                bm25_weight=0.5,
                vector_weight=0.5
            )
        else:
            hybrid_search = None

        return {
            'bm25': bm25_ranker,
            'vector': vector_searcher,
            'hybrid': hybrid_search
        }

    except Exception as e:
        logger.error(f"Error loading search system: {str(e)}")
        return None


# ===================================
# Main App
# ===================================

def main():
    st.title("🔍 Vietnamese Company Search Engine")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        search_method = st.radio(
            "Select Search Method",
            ["BM25 Search", "Vector Search", "Hybrid Search"],
            help="Choose between different search algorithms"
        )
        top_k = st.slider("Results per page", 5, 100, 10)

    # Load search systems
    search_system = load_search_system()

    if search_system is None:
        st.error("❌ Could not load search system. Please ensure indices are built.")
        st.info("Build indices using:")
        st.code("""
python -m src.indexer.index_builder data_sample/sample_cleaned.jsonl
python scripts/build_vector_index.py data_sample/sample_cleaned.jsonl
        """)
        return

    # Check if selected method is available
    if search_method == "Vector Search" and search_system['vector'] is None:
        st.warning("⚠️ Vector Search not available. Using BM25 instead.")
        search_method = "BM25 Search"

    if search_method == "Hybrid Search" and search_system['hybrid'] is None:
        st.warning("⚠️ Hybrid Search not available. Using BM25 instead.")
        search_method = "BM25 Search"

    # Search Interface
    st.header("🔎 Search")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Enter search query",
            placeholder="e.g., công ty công nghệ, nhà hàng hà nội, ...",
            label_visibility="collapsed"
        )
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)

    # Display results
    if search_button and query:
        search_start = time.time()

        try:
            if search_method == "BM25 Search":
                results = search_system['bm25'].rank_documents(
                    query_terms=query.lower().split(),
                    top_k=top_k
                )
                st.info(f"🔍 BM25 Search Results for: `{query}`")

            elif search_method == "Vector Search":
                results = search_system['vector'].search(query, top_k=top_k)
                st.info(f"🤖 Vector Search Results for: `{query}`")

            elif search_method == "Hybrid Search":
                results = search_system['hybrid'].search(query, top_k=top_k, return_details=True)
                st.info(f"⚡ Hybrid Search Results for: `{query}`")

            search_time = (time.time() - search_start) * 1000

            # Display search stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Results Found", len(results))
            with col2:
                st.metric("Search Time (ms)", f"{search_time:.2f}")
            with col3:
                st.metric("Search Method", search_method)

            # Display results
            st.markdown("---")
            st.subheader(f"📊 Top {len(results)} Results")

            for idx, (doc_id, score, doc) in enumerate(results, 1):
                with st.container():
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        st.markdown(f"### #{idx} - {doc.get('Tên doanh nghiệp', 'N/A')}")

                    with col2:
                        if search_method == "BM25 Search":
                            st.markdown(f"<span class='score-badge bm25-badge'>Score: {score:.2f}</span>",
                                      unsafe_allow_html=True)
                        elif search_method == "Vector Search":
                            st.markdown(f"<span class='score-badge vector-badge'>Score: {score:.2f}</span>",
                                      unsafe_allow_html=True)
                        elif search_method == "Hybrid Search":
                            st.markdown(f"<span class='score-badge hybrid-badge'>Score: {score:.2f}</span>",
                                      unsafe_allow_html=True)

                    # Display document details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Tax ID**: {doc.get('Mã số thuế', 'N/A')}")
                        st.write(f"**Industry**: {doc.get('Ngành nghề kinh doanh', 'N/A')}")
                    with col2:
                        st.write(f"**Address**: {doc.get('Địa chỉ', 'N/A')}")
                        st.write(f"**Status**: {doc.get('Tình trạng hoạt động', 'N/A')}")

                    # Show score breakdown if hybrid
                    if search_method == "Hybrid Search" and "_hybrid_scores" in doc:
                        breakdown = doc["_hybrid_scores"]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**BM25 Score**: {breakdown['bm25']:.2f}")
                        with col2:
                            st.write(f"**Vector Score**: {breakdown['vector']:.2f}")
                        with col3:
                            st.write(f"**Hybrid Score**: {breakdown['hybrid']:.2f}")

                    st.markdown("---")

        except Exception as e:
            st.error(f"❌ Error during search: {str(e)}")
            logger.exception("Search error")

    # Footer
    st.markdown("---")
    st.markdown("""
    **Project**: SEG301 - Search Engine & Information Retrieval
    **Team**: UnderFitting
    **Methods**: BM25 + Vector Search + Hybrid Ranking
    """)


if __name__ == "__main__":
    main()
