# Benchmark Report

Total results: 972

## Variant Summary

| Variant | RAGAS | Recall@5 | Faithfulness | Citation Accuracy | Temporal Accuracy | P95 Latency | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive_dense_only | 0.611 | 0.435 | 1.000 | 1.000 | 1.000 | 0ms | 0.0000 |
| standard_hybrid | 0.743 | 0.435 | 1.000 | 1.000 | 1.000 | 16ms | 0.0000 |
| standard_no_rerank | 0.584 | 0.435 | 1.000 | 1.000 | 1.000 | 0ms | 0.0000 |

## Query Type Breakdown

| Query Type | Best Variant | Worst Variant | Main Failure |
|---|---|---|---|
| open_book_qa | standard_hybrid | standard_no_rerank | low_recall |

## Component Contribution

| Component | Quality Gain | Latency Cost | Recommendation |
|---|---:|---:|---|
| Reranking | 0.159 | 4ms | keep |

## Sample Queries

| Query | Type | Best Variant |
|---|---|---|
| Why Deep Fried Foods May Cause Cancer | open_book_qa | standard_hybrid |
| Living Longer by Reducing Leucine Intake | open_book_qa | standard_hybrid |
| Why are Cancer Rates so Low in India? | open_book_qa | standard_hybrid |
| Peeks Behind the Egg Industry Curtain | open_book_qa | standard_hybrid |
| Organic Milk and Prostate Cancer | open_book_qa | naive_dense_only |
| Foods for Macular Degeneration | open_book_qa | standard_hybrid |
| How Beans Help Our Bones | open_book_qa | standard_hybrid |
| Phosphate Additives in Chicken Banned Elsewhere | open_book_qa | naive_dense_only |
| How to Boost the Benefits of Exercise | open_book_qa | standard_hybrid |
| How to Treat Multiple Sclerosis With Diet | open_book_qa | standard_hybrid |
| How to Get Kids to Eat Their Vegetables | open_book_qa | standard_hybrid |
| Citrus to Reduce Muscle Fatigue | open_book_qa | standard_hybrid |
| Can We Fight the Blues With Greens? | open_book_qa | naive_dense_only |
| Dealing With Air Travel Radiation Exposure | open_book_qa | naive_dense_only |
| How Probiotics Affect Mental Health | open_book_qa | standard_hybrid |
| Down But Not Out | open_book_qa | standard_hybrid |
| Cinnamon for Diabetes | open_book_qa | naive_dense_only |
| The Best Nutrition Bar | open_book_qa | standard_hybrid |
| Why are Children Starting Puberty Earlier? | open_book_qa | standard_hybrid |
| Foods That May Block Cancer Formation | open_book_qa | standard_hybrid |
