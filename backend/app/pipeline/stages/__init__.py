"""Pipeline stage result types — one import point for all ingestion stage results."""

from app.workers.chunking import ChunkingRunResult as ChunkingStageResult
from app.workers.dense_indexing import DenseIndexingRunResult as DenseIndexingStageResult
from app.workers.extraction import ExtractionRunResult as ExtractionStageResult
from app.workers.sparse_indexing import SparseIndexingRunResult as SparseIndexingStageResult

__all__ = [
    "ChunkingStageResult",
    "DenseIndexingStageResult",
    "ExtractionStageResult",
    "SparseIndexingStageResult",
]
