"""Evaluation dataset loaders for benchmark harness."""

from tests.evaluation.datasets.beir_loader import (
    BEIRLoader,
    BEIRCorpusEntry,
    BEIRQuery,
    BEIRQrel,
    load_corpus,
    load_queries,
    load_qrels,
)

__all__ = [
    "BEIRLoader",
    "BEIRCorpusEntry",
    "BEIRQuery",
    "BEIRQrel",
    "load_corpus",
    "load_queries",
    "load_qrels",
]