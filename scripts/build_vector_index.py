#!/usr/bin/env python3
"""Wrapper script for building vector index."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indexer.build_vector_index import main

if __name__ == '__main__':
    main()
