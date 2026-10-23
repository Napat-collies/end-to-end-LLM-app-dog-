# Retrieval evaluation

32 labelled questions (22 EN, 10 TH) over 40 Wikipedia articles. A hit = a chunk from a relevant breed's article. Embeddings: bge-m3.

## 1. Retriever comparison (chunk size 250 words)

| Retriever | Recall@1 | Recall@3 | Recall@5 | MRR@10 | Recall@5 EN | Recall@5 TH |
|---|---|---|---|---|---|---|
| BM25 (baseline) | 0.672 | 0.688 | 0.688 | 0.688 | 1.0 | 0.0 |
| Dense bge-m3 | 0.922 | 0.969 | 1.0 | 0.956 | 1.0 | 1.0 |
| Hybrid (RRF) | 0.891 | 0.969 | 1.0 | 0.94 | 1.0 | 1.0 |

## 2. Chunk-size sweep (dense, 15% overlap)

| Chunk size (words) | # chunks | Recall@1 | Recall@3 | Recall@5 | MRR@10 |
|---|---|---|---|---|---|
| 100 | 1170 | 0.922 | 0.969 | 1.0 | 0.961 |
| 250 | 608 | 0.922 | 0.969 | 1.0 | 0.956 |
| 500 | 474 | 0.922 | 0.969 | 1.0 | 0.956 |

## 3. min_score sweep (dense; 0.0 = naive default, no floor)

| min_score | Answerable kept | Unanswerable rejected | Off-topic rejected | Uncovered breed rejected | Balanced acc. |
|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| 0.3 | 1.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| 0.35 | 1.0 | 0.1 | 0.167 | 0.0 | 0.55 |
| 0.4 | 1.0 | 0.4 | 0.667 | 0.0 | 0.7 |
| 0.45 | 1.0 | 0.7 | 1.0 | 0.25 | 0.85 |
| 0.5 | 1.0 | 0.8 | 1.0 | 0.5 | 0.9 |
| 0.55 | 0.906 | 0.9 | 1.0 | 0.75 | 0.903 |
| 0.6 | 0.75 | 1.0 | 1.0 | 1.0 | 0.875 |
| 0.65 | 0.531 | 1.0 | 1.0 | 1.0 | 0.766 |
| 0.7 | 0.219 | 1.0 | 1.0 | 1.0 | 0.609 |

Best balanced accuracy: min_score = 0.55 (config.MIN_SCORE is currently 0.45).

Best-score ranges - answerable: 0.506..0.741; unanswerable: 0.325..0.567

## 4. Failures of the best retriever (dense, Recall@5 < 1)

No failures at Recall@5.
