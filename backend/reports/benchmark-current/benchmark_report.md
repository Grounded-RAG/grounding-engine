# Benchmark Report

Total results: 20

## Variant Summary

| Variant | RAGAS | Recall@5 | Faithfulness | Citation Accuracy | Temporal Accuracy | P95 Latency | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| enterprise_temporal_no_freshness | 0.638 | 0.750 | 0.613 | 0.708 | 0.250 | 0ms | 0.0000 |
| enterprise_temporal_rag | 0.638 | 0.750 | 0.613 | 0.875 | 0.750 | 0ms | 0.0000 |
| naive_dense_only | 0.701 | 0.750 | 0.613 | 0.458 | 0.250 | 0ms | 0.0000 |
| standard_hybrid | 0.638 | 0.750 | 0.613 | 0.708 | 0.250 | 0ms | 0.0000 |
| standard_no_rerank | 0.701 | 0.750 | 0.613 | 0.458 | 0.250 | 0ms | 0.0000 |

## Query Type Breakdown

| Query Type | Best Variant | Worst Variant | Main Failure |
|---|---|---|---|
| contradiction | naive_dense_only | naive_dense_only | low_faithfulness |
| insufficient_evidence | naive_dense_only | standard_hybrid | low_recall |
| temporal_policy | naive_dense_only | naive_dense_only | low_faithfulness |

## Component Contribution

| Component | Quality Gain | Latency Cost | Recommendation |
|---|---:|---:|---|
| Reranking | -0.062 | 0ms | review |
| Temporal scoring | 0.000 | 0ms | keep |
