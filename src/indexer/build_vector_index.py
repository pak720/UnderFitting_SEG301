#!/usr/bin/env python3
"""Build vector index from JSONL data."""

import argparse
import sys
import logging
from pathlib import Path

try:
    from src.indexer.vector_indexer import VectorIndexer
except ImportError:
    from .vector_indexer import VectorIndexer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Build vector index from JSONL file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('jsonl_path', help='Path to input JSONL file')
    parser.add_argument(
        '--index-dir', default='vector_index',
        help='Output directory for the vector index'
    )
    parser.add_argument(
        '--model', default='distiluse-base-multilingual-cased-v2',
        help='Sentence-Transformers model name'
    )
    parser.add_argument(
        '--batch-size', type=int, default=None,
        help='Encoding batch size (default: 256 on GPU, 32 on CPU)'
    )
    parser.add_argument(
        '--device', default='auto', choices=['auto', 'cpu', 'cuda'],
        help='Compute device — auto picks GPU when available'
    )
    parser.add_argument(
        '--fp16', action='store_true', default=False,
        help='Use half-precision (FP16) on GPU for ~2x speed'
    )
    parser.add_argument(
        '--max-docs', type=int, default=None,
        help='Index only the first N documents'
    )
    parser.add_argument(
        '--no-resume', action='store_true', default=False,
        help='Ignore existing checkpoint and rebuild from scratch'
    )
    parser.add_argument(
        '--prefetch', type=int, default=4,
        help='Number of batches to prefetch in the reader queue'
    )

    args = parser.parse_args()

    if not Path(args.jsonl_path).exists():
        logger.error(f"File not found: {args.jsonl_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Vector Index Builder")
    logger.info("=" * 60)
    logger.info(f"Input      : {args.jsonl_path}")
    logger.info(f"Output     : {args.index_dir}")
    logger.info(f"Model      : {args.model}")
    logger.info(f"Device     : {args.device}")
    logger.info(f"FP16       : {args.fp16}")
    logger.info(f"Batch size : {args.batch_size or 'auto'}")
    logger.info(f"Prefetch   : {args.prefetch} batches")
    if args.max_docs:
        logger.info(f"Max docs   : {args.max_docs}")
    logger.info(f"Resume     : {not args.no_resume}")
    logger.info("=" * 60)

    try:
        indexer = VectorIndexer(
            model_name=args.model,
            batch_size=args.batch_size,
            device=args.device,
            fp16=args.fp16,
        )

        indexer.build_index(
            jsonl_path=args.jsonl_path,
            index_dir=args.index_dir,
            max_docs=args.max_docs,
            resume=not args.no_resume,
            prefetch_batches=args.prefetch,
        )

        logger.info("=" * 60)
        logger.info("Vector index built successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
