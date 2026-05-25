# Demo Lecture: RAG Metrics

This is synthetic course material created for the public demo repository.

## Retrieval Metrics

Retrieval quality measures whether the system finds useful context before generation.

- Hit Rate at K: whether at least one relevant document appears in the top K results.
- MRR: mean reciprocal rank of the first relevant result.
- NDCG at K: ranking quality when results have graded relevance.
- Context precision: how much retrieved context is actually useful.
- Context recall: how much required evidence was retrieved.

## Answer Quality Metrics

Answer quality measures whether the final response is useful and grounded.

- Faithfulness: whether the answer is supported by retrieved context.
- Answer relevance: whether the answer addresses the user question.
- Completeness: whether all requested parts of the assignment are covered.
- Citation quality: whether cited sources match the claims.

## Practical Evaluation Loop

1. Create a small evaluation set of assignments and expected key points.
2. Run the agent on each assignment.
3. Store retrieved sources, draft answer, model name, and reviewer decision.
4. Track retrieval metrics and answer quality metrics.
5. Improve chunking, search, prompts, or model choice one change at a time.

For a student project, keyword search and JSON storage are acceptable for a first version. A vector database can be added later if retrieval quality becomes the bottleneck.

