# Standard Tier Current State

**Status:** current implemented Standard tier as of 2026-04-11

## Purpose

This document is the current handoff note for the implemented Standard tier.

It is meant to help a teammate quickly understand:

- what Standard does today
- how the live request path works
- which backend files matter most
- what behavior is intentional
- what is still reserved for Enterprise and Critical

If you only read one Standard document before continuing work, read this one.

Related documents:

- `docs/SOLUTION_ARCHITECTURE.md`
- `docs/STANDARD_TIER_PHASE1.md` (historical Phase 1 record)
- `docs/PHASE_2_ENTERPRISE_PLAN.md`
- `docs/PHASE_3_CRITICAL_PLAN.md`

---

## 1. Standard Tier Summary

Standard is Grounded's production baseline grounded RAG path.

It is designed to be:

- grounded
- traceable
- tenant-safe
- honest when support is weak
- fast enough for normal interactive use
- stronger than naive/basic RAG

Standard is no longer just:

- upload
- chunk
- retrieve
- answer

It now includes several quality layers on top of the basic RAG pattern:

- structure-aware chunking
- semi-structured document cleanup
- sparse + dense hybrid retrieval
- lightweight query planning
- lightweight query rewriting
- section-aware retrieval boosts
- lightweight reranking
- section-aware evidence packaging
- query-type-aware answer synthesis
- provider-backed generation
- safe deterministic fallback
- light answer validation
- degraded behavior
- trace persistence

---

## 2. Current Standard Scope

### Included in Standard

- tenant-scoped upload and ingestion
- TXT, PDF, and DOCX extraction
- structure-aware chunking
- chunk metadata for section-aware retrieval
- dense indexing in Qdrant
- sparse indexing in PostgreSQL
- hybrid retrieval with RRF
- lightweight query planning and follow-up carryover
- query-aware reranking
- section-aware evidence packaging
- query-aware grounded generation
- Gemini-backed generation
- local deterministic fallback generation
- response shaping with citations and confidence
- persisted query traces
- degraded and clarification responses

### Not included in Standard

These are intentionally kept for later tiers:

- model-based cross-encoder reranking
- heavy query decomposition / planner orchestration
- multi-hop retrieval planning
- temporal freshness scoring
- corrective retrieval loops
- critic / verification loop
- internal model retrieval
- external web fallback
- high-assurance Critical verification logic

---

## 3. End-To-End Runtime Flow

### Ingestion path

```text
upload
  -> extraction
  -> metadata enrichment
  -> structure-aware chunking
  -> sparse indexing in PostgreSQL
  -> dense indexing in Qdrant
  -> document becomes indexed
```

### Query path

```text
user query
  -> tenant + namespace validation
  -> small-talk / clarification gate
  -> query plan construction
  -> sparse retrieval
  -> dense retrieval
  -> RRF fusion
  -> lightweight reranking
  -> supporting context recovery
  -> evidence packaging
  -> generation backend selection
      -> Gemini provider when available
      -> local deterministic fallback when needed
  -> provider answer validation
  -> structured response shaping
  -> trace persistence
  -> answer + citations + confidence
```

This means Standard is a normal RAG pipeline **plus** query planning,
reranking, evidence shaping, and safe fallback behavior.

---

## 4. Key Standard Files

These are the main files a teammate should know first.

### Query entry and orchestration

- `backend/app/services/query.py`

What it does:

- namespace validation
- clarification handling for greetings / filler prompts
- conversation-context resolution
- query plan creation
- retrieval execution
- evidence packaging
- generation
- response shaping
- trace persistence

### Query analysis

- `backend/app/core/query_analysis.py`

What it does:

- normalize and typo-correct user queries
- classify query kind
- extract attribute terms
- extract context terms
- detect dataset-summary / list / action / comparison / entity / count queries
- carry lightweight multi-turn context
- build retrieval rewrites

Current Standard query kinds include:

- `summary`
- `definition`
- `boolean`
- `list`
- `lookup`
- `action`
- `comparison`
- `entity`
- `count`
- `open`

### Retrieval

- `backend/app/services/retrieval.py`

What it does:

- sparse retrieval from PostgreSQL full-text search
- dense retrieval from Qdrant
- fusion with Reciprocal Rank Fusion
- lightweight reranking by answerability
- section-aware retrieval bonuses
- supporting-context recovery from nearby chunks and same-section chunks
- namespace summary seed recovery for dataset-summary queries

### Evidence packaging

- `backend/app/services/evidence.py`

What it does:

- choose the best evidence package for the current query
- select one chunk for focused field extraction
- select structured bundles for list, action, comparison, entity, and count queries
- keep evidence compact enough for generation

### Local grounded generation

- `backend/app/core/llm_client.py`

What it does:

- deterministic grounded answer rendering from packaged evidence
- query-aware snippet selection
- dataset-summary rendering
- collection rendering
- action / comparison / entity / count rendering
- fallback path when provider-backed generation is unavailable or rejected

### Provider-backed generation

- `backend/app/services/generation.py`
- `backend/app/core/gemini_generator.py`

What they do:

- choose the configured generation backend
- send query + packaged evidence to Gemini
- validate provider output before returning it
- fall back to the deterministic local grounded generator if needed

Important recent note:

- Gemini generation previously fell back because the response schema sent to
  Gemini was invalid
- this was fixed by changing the provider output shape to a Gemini-compatible
  structured JSON response

### Response shaping and trust

- `backend/app/services/response_shaping.py`
- `backend/app/services/trust.py`

What they do:

- convert grounded drafts into API responses
- validate citation ids
- compute confidence
- label support strength
- mark degraded or ambiguous answers

### Ingestion / chunking

- `backend/app/pipeline/orchestrator.py`
- `backend/app/services/dense_indexing.py`

What they do:

- text cleanup during ingestion
- structure-aware chunk creation
- section metadata generation
- dense embedding and Qdrant payload creation

---

## 5. What Makes Standard Better Than Basic RAG

Compared with a naive/basic RAG system, Standard now adds:

- hybrid sparse + dense retrieval instead of vector-only search
- lightweight query planning instead of raw-query retrieval only
- section-aware chunk metadata
- section-aware retrieval bonuses
- lightweight reranking instead of flat top-k only
- evidence packaging instead of sending all retrieved chunks blindly
- provider answer validation before returning the answer
- deterministic grounded fallback
- degraded responses when support is weak
- persisted traces for debugging

Standard is still a RAG system, but it is no longer a naive one.

---

## 6. What Standard Is Good At

Standard is currently strongest on:

- normal document Q&A
- field extraction
- dataset summaries
- list-style questions
- action / responsibility questions
- yes/no questions with grounded support
- count questions with structured evidence
- sectioned documents
- semi-structured documents with bullets and key-value blocks

Typical examples:

- "What is this dataset about?"
- "What are the requirements?"
- "What are the technical skills?"
- "What did they do at company X?"
- "Did the document mention Y?"
- "How many projects are listed?"

---

## 7. Semi-Structured Document Handling

Standard now includes better handling for:

- wrapped bullets
- key-value layouts
- table-like rows
- OCR-ish line breaks
- section-heavy resumes and policy documents

This was added so Standard can work across more dataset types, not just clean
plain prose.

The key implementation lives in:

- `backend/app/pipeline/orchestrator.py`

Important limitation:

- Standard is improved for semi-structured docs, but it is still not a full
  table-understanding or OCR-specialist system

That deeper work can still grow later if needed.

---

## 8. Conversation Handling In Standard

Standard now includes lightweight long-history carryover.

It supports follow-ups like:

- "what about that"
- "and her certificates"
- "did it mention X there"
- "what about the second document"

This memory is intentionally lightweight and deterministic.

It is not the heavy planner-style long-horizon reasoning reserved for later
tiers.

---

## 9. Provider Behavior

Standard can generate through:

- `gemini_v1`
- `openai_compatible_v1`
- `local_grounded_v1`

In the current local setup, Standard is typically configured for:

- dense embeddings: Gemini
- generation: Gemini

Important runtime behavior:

- if the provider call fails, Standard falls back to the local grounded path
- if the provider answer is weakly aligned, Standard also falls back

That means the trace provider value matters a lot when debugging quality.

Examples:

- `gemini:gemini-2.5-flash`
  - provider answer was used
- `local-grounded-v1:fallback_from_gemini_v1`
  - provider path did not make it to the user and Standard used local fallback
- `clarification-handler-v1`
  - greeting / filler query path
- `degraded-handler-v1`
  - insufficient support path

---

## 10. How To Debug Standard Runs

When a teammate is checking a bad answer, inspect these in order:

1. the user query
2. the trace `generator_provider`
3. selected evidence ids
4. citation snippets
5. `verification_status`
6. `degraded_reasons`

Rule of thumb:

- if provider is `gemini:...`, the live provider answer reached the user
- if provider is `local-grounded-v1:fallback_from_gemini_v1`, the local path
  answered instead
- if citations are bad, first check retrieval/evidence selection
- if citations are good but wording is bad, check generation/rendering

---

## 11. Recent Important Fixes

These are the important Standard-quality changes that teammates should know are
already in place.

### Retrieval and evidence quality

- lightweight query planning added
- retrieval rewrites added
- section-aware chunk metadata added
- same-section and nearby-chunk context recovery added
- lightweight answerability reranking added
- better evidence packaging for list/action/comparison/count queries added

### Generation quality

- better dataset-summary rendering
- better list / collection rendering
- better action / comparison / entity / count rendering
- better small-talk clarification handling

### Provider integration

- Gemini response schema fixed so provider-backed generation actually works
- provider validation kept in place to reject weak grounded answers

### Recent outline-heading bug

A real bug was recently fixed where collection answers on paper-like documents
could return outline headings such as:

- `2. New Opportunities in Software Engineering`
- `3. New Challenges in Software Engineering`

instead of the real challenge content.

The fix now filters those heading-style artifacts more aggressively in the local
grounded renderer.

---

## 12. What Is Still Left For Enterprise And Critical

The following work is intentionally still outside Standard:

### Enterprise

- model-based reranker
- heavier query decomposition
- multi-hop retrieval planning
- larger-scale retrieval intelligence
- stronger long-horizon reasoning over harder chats

### Critical

- verification loop
- corrective retrieval
- stricter support validation
- higher-assurance answer policies
- internal model retrieval
- web fallback under strict policy

---

## 13. Recommended Team Rule

If Standard behavior changes in code, update at least:

- this document
- `docs/SOLUTION_ARCHITECTURE.md`

in the same batch.

That prevents the docs from drifting behind the actual runtime again.

---

## 14. Practical Next Step For Teammates

If someone picks up Standard work next, the best continuation order is:

1. review this document
2. inspect `query.py`, `query_analysis.py`, `retrieval.py`, `evidence.py`,
   `llm_client.py`, `generation.py`
3. read the Standard unit tests and golden quality cases
4. only then start Enterprise work such as model-based reranking

This keeps future work grounded in the real current system, not in an outdated
Phase 1-only mental model.
