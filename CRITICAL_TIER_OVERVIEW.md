# Critical Tier Overview

## What is the Critical Tier?

The Critical tier is the highest-assurance mode in the system.

Its job is not only to answer a question, but to make sure the answer is truly supported by evidence before accepting it.

In simple terms:

- Standard: gets grounded evidence and answers with citations
- Enterprise: improves retrieval quality for harder questions
- Critical: verifies whether the answer should be trusted at all

## The 11 Stages

1. Query transformation
- Rewrites the question into a retrieval-friendly form.

2. Semantic chunking
- Splits documents into meaningful chunks with structure.

3. Namespace isolation
- Keeps retrieval inside the correct tenant and dataset.

4. Hybrid retrieval
- Uses both keyword and semantic retrieval.

5. Temporal ranking
- Prefers fresher evidence when recency matters.

6. Reranking
- Reorders results to improve relevance.

7. Corrective retrieval behavior
- Retries once when support is weak.

8. Internal retrieval support
- Expands the evidence set using already retrieved grounded chunks.

9. Verification loop
- Checks answer claims against the evidence.

10. Structured enforcement
- Forces final outputs into a safe, consistent shape.

11. Source attribution
- Returns citations tied to specific evidence chunks.

## What belongs to Critical?

The main Critical-specific additions are:

1. Corrective retrieval behavior
2. Internal retrieval support
3. Verification loop
4. Structured enforcement

Critical also depends on the lower-tier foundation:

- query transformation
- semantic chunking
- namespace isolation
- hybrid retrieval
- temporal ranking
- reranking
- source attribution

## What We Added in Critical

### 1. Corrective Retrieval Behavior

What it means:
- If the first answer is weak, we do one bounded retry.

Why it exists:
- The first retrieval can miss an important term.
- Critical should get one safe second chance, not unlimited retries.

What we implemented:
- one retry only
- retry only for recoverable weak-support cases
- retry query built from missing claim terms
- retry metadata stored in traces
- fixed a bug where retry results were not returned properly

Why it matters:
- Critical becomes strict without being too brittle.

### 2. Internal Retrieval Support

What it means:
- Critical can widen the evidence set using already retrieved grounded chunks.

Why it exists:
- Sometimes the answer is close, but the selected evidence is too narrow.

What we implemented:
- bounded internal evidence expansion
- expansion only from already retrieved grounded hits
- policy-gated behavior
- re-verification after expansion
- metadata showing whether internal retrieval was attempted and used

Why it matters:
- Critical can recover safely without inventing evidence.

### 3. Verification Loop

What it means:
- Critical checks the answer before trusting it.

Why it exists:
- A grounded generator can still overstate or partially miss what the evidence says.

What we implemented:
- claim extraction
- support scoring
- contradiction detection
- unsupported and partial-support detection
- retry term extraction from failed claims
- structured verifier metadata in traces

How decisions work:
- accept: claims are supported
- degrade: support is partial or weak
- refuse: claims are unsupported or contradicted

Why it matters:
- Answers are accepted because they pass evidence checks, not because they sound confident.

### 4. Structured Enforcement

What it means:
- Final Critical responses must follow strict output rules.

Why it exists:
- Without enforcement, outputs can become inconsistent.

Examples of bad states:
- passed but still marked partial
- degraded with no clear reason
- weak answer still looking too confident

What we implemented:
- final critical response normalization
- consistent passed/degraded response shapes
- preserved recovery-path metadata in traces
- stronger trace consistency after retry and recovery

Accepted Critical responses are normalized to:
- `verification_status = passed`
- `support_summary = grounded`
- `degraded_reasons = []`

Degraded Critical responses are normalized to:
- explicit degraded reasons
- low confidence
- partial or insufficient support summary

Why it matters:
- Final outputs are safer, clearer, and easier to audit.

## What Tools / Models Did We Use?

### What is the generation model?

- **Gemini** (Google's model) is used as the answer generation model.
- The system supports multiple backends, but when configured, Gemini generates the answer.
- Critical is the verification layer on top of the generation model.

### Simple way to present it:

> Gemini generates the answer. Critical verifies whether the answer should be accepted.

Critical does NOT use a different model. It adds a verification layer on top of the same model used by Standard and Enterprise.

### What other tools does Critical use?

1. **Hybrid retrieval** - combines dense (embedding) and sparse (keyword) search
2. **Evidence packaging** - selects and organizes retrieved chunks
3. **Claim extraction** - splits the answer into verifiable claims
4. **Support matching** - checks each claim against evidence
5. **Contradiction detection** - finds conflicting evidence
6. **Retry term generation** - extracts missing terms for corrective retry

### Key distinction

- **Standard/Enterprise**: retrieve evidence -> generate answer -> return answer
- **Critical**: retrieve evidence -> generate answer -> verify answer -> enforce output rules

Critical adds verification between generation and returning the answer.

## Short Summary

Critical adds four main things:

1. one bounded retry when support is weak
2. bounded internal evidence expansion
3. claim-by-claim verification against evidence
4. strict final response enforcement

This makes Critical the highest-assurance mode in the system.
