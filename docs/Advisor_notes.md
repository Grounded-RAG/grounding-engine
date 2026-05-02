# Advisor Notes

**Status:** cleaned and structured handoff as of 2026-04-11

## Purpose

This document captures the advisor's expectations for the project in a
practical form that the team can use while building, evaluating, and preparing
the final report and demo.

It exists to answer three questions clearly:

- what the project must deliver
- how the system should be evaluated and presented
- what evidence is needed to prove the work is strong

This document should be read alongside:

- `docs/STANDARD_TIER_CURRENT_STATE.md`
- `docs/NEXT_PHASES_ROADMAP.md`
- `docs/SOLUTION_ARCHITECTURE.md`

---

## 1. Executive Summary

The project is not just to build a working RAG prototype.

It is to build, evaluate, and demonstrate an **advanced RAG system** that is:

- measurably better than a naive baseline
- grounded and citation-aware
- benchmarked with real metrics
- analyzed for failures, not only successes
- explained as both an engineering system and a product-ready solution

The final outcome should show:

- technical depth
- practical delivery value
- clear benchmark evidence
- a functioning demo
- readable documentation

---

## 1.1 Phase Classification Of Advisor Requirements

The advisor requirements are broader than one implementation phase.

They should be interpreted across the roadmap like this.

### Phase 1: Standard baseline

Primary responsibility:

- make the core grounded RAG system work end to end

What this phase should cover:

- ingestion
- cleaning and preparation
- chunking
- embedding and indexing
- retrieval
- baseline grounded answer generation
- citations
- confidence/support shaping
- initial evaluation scaffolding
- initial demo path

Typical advisor-aligned outputs from this phase:

- working end-to-end RAG flow
- citations visible in answers
- baseline confidence explanation
- first benchmark cases
- first naive vs improved comparisons

### Phase 2: Enterprise tier

Primary responsibility:

- show measurable retrieval and evidence-quality uplift over Standard / naive
  baselines

What this phase should cover:

- reranking
- query expansion / decomposition
- harder-query retrieval improvements
- stronger evidence packaging
- benchmark uplift measurement
- A/B comparison against simpler retrieval paths

Typical advisor-aligned outputs from this phase:

- reranking evaluation
- improved ranking metrics
- better hotspot-question handling
- stronger baseline-vs-improved tables

### Phase 3: Critical tier

Primary responsibility:

- improve faithfulness, unsupported-claim handling, and assurance

What this phase should cover:

- verifier / critic behavior
- stronger unsupported-claim rejection
- stronger confidence trust signals
- higher-assurance answer acceptance
- clearer failure handling

Typical advisor-aligned outputs from this phase:

- faithfulness improvements
- lower unsupported-claim rate
- clearer confidence interpretation
- stronger high-risk failure analysis

### Phase 4: Adaptive Grounding

Primary responsibility:

- formalize source-aware behavior when the system goes beyond strict dataset
  lookup

What this phase should cover:

- source-aware policy
- explicit grounded vs model-derived disclosure
- clearer handling of explanatory or mixed-source questions

Typical advisor-aligned outputs from this phase:

- source-aware policy explanation
- clearer disclosure behavior
- better explanation of grounded vs augmented answers

### Phase 5: Platform Maturity

Primary responsibility:

- make the system deployable and product-ready

What this phase should cover:

- authentication
- JWT support
- dataset isolation
- multi-tenant readiness
- deployment architecture
- demo operability
- observability and admin readiness

Typical advisor-aligned outputs from this phase:

- deployment section
- security section
- multi-tenant/product readiness explanation
- stronger demo and operating story

### Phase 6: Optimization

Primary responsibility:

- produce the strongest final evaluation and polish the system for final
  presentation

What this phase should cover:

- benchmark expansion
- failure replay
- metric tuning
- confidence calibration
- tables and visualizations
- final A/B reporting
- report polish

Typical advisor-aligned outputs from this phase:

- final benchmark tables
- visualizations
- calibration analysis
- refined failure analysis
- final recommendations section

### Important interpretation rule

The advisor requirements are **cumulative**, not isolated.

That means:

- Phase 1 starts the proof
- later phases strengthen the proof
- the final report should present the whole system as one evaluated project

---

## 2. Core Problem Statement

The project should solve this problem:

> Build a RAG system that answers questions accurately, faithfully, and
> efficiently from source documents while providing citations, confidence
> estimates, and measurable improvement over simpler baselines.

The advisor notes make it clear that naive RAG is not enough because it often
fails through:

- irrelevant or incomplete retrieval
- missing context
- unsupported answer generation
- unstable performance across question types
- weak faithfulness
- poor benchmarking
- unclear confidence behavior

The project should explicitly show how the improved system reduces those
failures.

---

## 3. Main Objectives

### 3.1 Build a complete RAG pipeline

The system should cover the full path from ingestion to answer delivery:

- document cleaning and preparation
- chunking
- embedding and indexing
- retrieval
- reranking
- context assembly
- answer generation
- citation generation
- confidence scoring
- response delivery

### 3.2 Build a real evaluation setup

The project must include a benchmark dataset with ground-truth answers.

This is not optional.

### 3.3 Compare against baselines

The improved system should be evaluated against at least:

- a naive RAG baseline
- one or more improved RAG variants
- where feasible, comparison against industry-style RAG approaches

### 3.4 Use quantifiable metrics

The report must use numerical evidence, not just qualitative impressions.

### 3.5 Deliver a working demo

The demo should show:

- answer generation
- citations
- confidence explanation
- ideally a public URL if feasible

### 3.6 Address product and deployment concerns

The implementation and report should cover:

- code structure
- deployment design
- authentication
- dataset isolation
- multi-tenant readiness
- JWT-based security
- documentation quality

---

## 4. Data and Source Document Requirements

The report must explain the data clearly.

### 4.1 Data description

Describe:

- what documents were used
- where they came from
- their formats
- their volume
- their domain coverage
- whether they contained corruption, noise, or formatting problems

### 4.2 Source references

Include links, references, or a clear description of the source collection.

### 4.3 Data quality discussion

The advisor notes strongly imply that document cleanup matters.

The report should explain:

- whether the documents were noisy or corrupted
- what cleanup steps were required
- why this matters for retrieval quality

### 4.4 Benchmark set construction

The benchmark set should include, where possible:

- question
- ground-truth answer
- expected source document(s)
- expected supporting chunk(s)
- question category or difficulty
- optional failure / hotspot annotations

---

## 5. Mandatory Deliverables

The following are required.

### 5.1 Evaluation-ready benchmark dataset

The project must include a test set with ground-truth answers.

It should support:

- retrieval evaluation
- generation evaluation
- case analysis
- failure analysis
- hotspot-question analysis
- A/B testing

### 5.2 Baseline comparison

The final work must compare:

- naive RAG
- improved RAG stages
- possibly industry-style configurations where feasible

### 5.3 Tables and visualizations

Results should be presented through:

- clear tables
- charts
- comparison summaries

### 5.4 Working demo

The demo must show:

- a complete RAG flow
- citations
- confidence explanation
- documentation for how to run and inspect it

### 5.5 Technical and deployment documentation

The documentation should explain:

- architecture
- setup
- API usage
- deployment
- demo instructions
- security
- evaluation procedure

---

## 6. Evaluation Strategy

The advisor notes place strong emphasis on evaluation depth.

### 6.1 Evaluation questions to answer

The evaluation should answer:

- does the retriever find the right chunks?
- does it retrieve enough context to answer correctly?
- does the generator stay faithful to the retrieved evidence?
- how often does the system hallucinate or overclaim?
- how much better is the system than naive RAG?
- what quality-vs-latency tradeoffs exist?
- which pipeline stages contribute most to success or failure?

### 6.2 Evaluation layers

The project should evaluate multiple levels, not only end-to-end output.

#### Retrieval-level evaluation

Measure whether relevant content is retrieved.

#### Reranking-level evaluation

Measure whether reranking improves the ordering of relevant chunks.

#### Context-level evaluation

Measure whether the final evidence package contains enough support to answer.

#### Generation-level evaluation

Measure whether the answer is correct, faithful, and properly cited.

#### End-to-end evaluation

Measure the full pipeline from query to final response.

---

## 7. Quantifiable Metrics

The report should use explicit metrics and report them numerically.

### 7.1 Retrieval metrics

Recommended retrieval metrics:

- Recall@k
- Precision@k
- Mean Reciprocal Rank (MRR)
- nDCG
- Hit Rate@k
- Context Recall
- Chunk Retrieval Accuracy

### 7.2 Answer quality metrics

Recommended answer-quality metrics:

- Exact Match (EM), where applicable
- F1 overlap
- answer correctness
- faithfulness
- citation correctness
- hallucination rate
- unsupported claim rate

### 7.3 System performance metrics

Recommended system metrics:

- end-to-end latency
- retrieval latency
- reranking latency
- generation latency
- total response delay
- throughput
- index size / storage footprint
- cost per query, where relevant

### 7.4 Confidence-related metrics

Because confidence scoring is required, report:

- confidence calibration quality
- confidence-vs-correctness correlation
- false high-confidence rate
- wrong answers hidden behind medium/high confidence
- confidence behavior by question type

---

## 8. Faithfulness and Evaluation Framing

### 8.1 Faithfulness

Faithfulness is essential in RAG.

The report should distinguish between:

- answers that sound fluent
- answers that are actually supported by evidence

### 8.2 Target-aware evaluation

The evaluation targets should be defined clearly:

- retrieval target = relevant chunk(s)
- context target = sufficient evidence set
- generation target = ground-truth answer
- citation target = supporting source document(s)

### 8.3 Evaluation framework choice

The report should explain which framework or methodology is used for:

- retrieval benchmarking
- faithfulness checking
- answer correctness
- citation validation
- failure categorization

The emphasis should remain on reproducible, measurable evaluation.

---

## 9. Baselines and Benchmarking

### 9.1 Naive RAG baseline

The naive baseline should be defined clearly, for example:

- standard chunking
- vector similarity search
- no reranking
- no query expansion
- no decomposition
- no confidence scoring
- direct answer generation from top-k retrieved chunks

### 9.2 Improved RAG stages

The improved system should be evaluated in stages, for example:

1. Naive RAG
2. RAG + cleaned documentation
3. RAG + better chunking / indexing
4. RAG + reranking
5. RAG + confidence scoring
6. RAG + query expansion / decomposition
7. Full advanced RAG pipeline

This staged evaluation helps show where quality gains come from.

### 9.3 A/B testing

A/B testing should compare systems on the same benchmark set, for example:

- naive RAG vs reranked RAG
- reranked RAG vs reranked + query expansion
- full pipeline vs an industry-style baseline

It should report differences in:

- accuracy
- faithfulness
- recall / precision
- latency
- user-facing quality

### 9.4 Industry comparison

Where feasible, the report should compare the solution against common
industry-style RAG approaches conceptually or empirically.

Useful comparison dimensions:

- retrieval quality
- reranking usage
- citation support
- faithfulness handling
- confidence scoring
- latency tradeoffs
- deployment readiness
- multi-tenant safety

---

## 10. Hotspot Questions and Failure Analysis

The advisor notes clearly expect depth, not only success cases.

### 10.1 Hotspot questions

Include questions that expose important weaknesses, such as:

- ambiguous questions
- multi-document questions
- long-context questions
- noisy-document questions
- apparently answerable questions that actually lack enough evidence

### 10.2 Failure analysis

The report should include a dedicated failure-analysis section.

Failures can be grouped by stage:

#### Retrieval failures

- relevant chunk not retrieved
- relevant chunk ranked too low
- noisy or corrupted source text misleads retrieval

#### Context construction failures

- insufficient evidence passed to the generator
- chunk boundaries remove necessary context
- context contains too much irrelevant material

#### Generation failures

- partially correct but unsupported answer
- hallucinated details
- wrong synthesis from correct evidence

#### Confidence failures

- high confidence on wrong answers
- low confidence on correct answers

---

## 11. Confidence Score Explanation

Each demo answer should explain confidence clearly.

The project should explain:

- what the confidence score represents
- what signals it uses
- how users should interpret high, medium, and low confidence

Possible inputs may include:

- top retrieval score
- reranker margin
- number of supporting chunks
- citation agreement
- answer consistency

The report should define the actual method used, not hand-wave it.

---

## 12. LLM Generation and Codebase Explanation

The report should explain the generation layer in terms of both:

- modeling behavior
- code structure

It should cover:

- model selection
- prompting strategy
- how retrieved chunks are formatted
- citation injection
- answer post-processing
- confidence computation
- error handling
- logging
- modular code structure

It should also explain how generation interacts with:

- retrieval
- reranking
- confidence logic
- product-facing APIs

---

## 13. Complete Pipeline Architecture

The final report should present the full pipeline clearly.

An end-to-end architecture can include:

- document ingestion
- cleaning corrupted documentation
- chunking
- embedding generation
- indexing
- query preprocessing
- query expansion and decomposition
- initial retrieval
- reranking
- context selection
- answer generation
- citation grounding
- confidence scoring
- response serving
- evaluation logging and analytics

The report should include a visual diagram of this flow.

---

## 14. Demo Requirements

The project must include a working demo.

### The demo should show

- a user entering a question
- the system retrieving evidence
- the final answer
- citations to source documents
- confidence score explanation
- ideally a public URL if feasible

### Demo documentation should explain

- how to run it
- how to access it
- how citations are shown
- what confidence means
- known limitations

---

## 15. Security and Product Requirements

The advisor notes also expect product-level thinking.

### 15.1 Authentication

The system should define or implement authentication for the demo/deployment.

### 15.2 Dataset isolation

The system should isolate datasets, especially for multi-user or multi-tenant
use.

### 15.3 JWT

JWT-based authentication / authorization should be implemented or clearly
planned.

### 15.4 Multi-tenant readiness

Multi-tenant design should be discussed as a medium-priority capability.

### 15.5 Source-aware policy

The system should respect document origin, permissions, and retrieval
boundaries.

---

## 16. Deployment Expectations

The report should explain deployment in practical terms.

It should cover:

- system architecture
- backend/API service
- vector database or retrieval store
- model serving
- authentication service
- demo frontend
- hosting approach

It should also discuss:

- scalability
- caching
- latency optimization
- monitoring
- public demo access if relevant

---

## 17. Presentation of Results

The advisor specifically asked for results in table form and with
visualizations.

### 17.1 Tables to include

Recommended tables:

- baseline vs improved system metrics
- retrieval performance by method
- latency by stage
- faithfulness / correctness by question type
- confidence calibration summary
- failure-category counts

### 17.2 Visualizations to include

Recommended charts:

- Recall@k comparison
- Precision@k comparison
- latency breakdown
- confidence-vs-correctness plot
- ablation study chart
- failure distribution chart
- A/B testing comparison

---

## 18. Actionable Recommendations Section

The final report should end with recommendations, not just observations.

Possible recommendation themes:

- improve chunking for long-context documents
- expand the benchmark dataset
- tune reranker thresholds
- calibrate confidence scores
- reduce latency through caching
- improve source-aware filtering
- strengthen multi-tenant isolation

---

## 19. Suggested Weekly Roadmap

### Week 1

High priority:

- clean corrupted documentation
- integrate the LLM
- benchmark against existing baselines

### Week 2

High priority:

- add reranking, ideally with a cross encoder
- implement confidence scoring
- prepare a public demo URL if feasible

Medium priority:

- add query expansion and decomposition
- complete ranking evaluation
- add multi-tenant support

### Later phase

Lower priority:

- thinking-mode style deeper reasoning
- source-aware policy logic
- performance optimization and caching

---

## 20. Priority Interpretation

### Must-have

- working RAG system
- test set with ground truth
- naive vs improved baseline comparison
- quantified metrics
- tables and visualizations
- citation-enabled demo
- confidence explanation
- documentation
- basic deployment
- basic security
- failure analysis

### Medium priority

- query expansion
- query decomposition
- multi-tenant design
- richer ranking evaluation

### Lower priority

- thinking mode
- advanced policy logic
- aggressive performance optimization
- more advanced caching strategies

---

## 21. Graduation Requirement

The notes effectively reduce to one practical rule:

> Make it work.

At minimum, the following must work end to end:

- documents can be ingested
- questions can be asked
- retrieval works
- reranking works
- the LLM generates answers
- citations are shown
- confidence is explained
- evaluation numbers are reported

A polished report without a convincing working system is not enough.

---

## 22. Final Expected Outcome

By the end of the project, the expected result is:

- a complete advanced RAG pipeline
- a benchmark dataset with ground-truth answers
- a quantitative evaluation report
- baseline comparisons against naive and stronger methods
- tables and visualizations
- A/B testing evidence
- failure-case analysis
- a working demo with citations and confidence scores
- basic security and deployment support
- clear documentation

The final output should read as both:

- an engineering solution
- an evaluated research-style system

---

## 23. Advisor-Aligned Suggestions For This Repo

Based on the current Grounded architecture, the most important practical
suggestions are:

1. keep Standard stable and benchmarked instead of changing it casually
2. build Enterprise around measurable reranking and planner uplift
3. create a true benchmark dataset with gold answers and evidence labels
4. report retrieval metrics and answer metrics separately
5. keep a visible failure-analysis section in every major phase
6. make the confidence explanation concrete and reproducible
7. prepare one demo flow that is easy for an advisor to inspect quickly
8. keep architecture docs and evaluation docs updated in the same PRs as code

---

## 24. One-Paragraph Proposal Summary

This project focuses on building and evaluating a complete Advanced
Retrieval-Augmented Generation pipeline that improves over naive RAG through
better data preparation, retrieval, reranking, confidence scoring, and
deployment-ready design. A benchmark dataset with ground-truth answers will be
created from source documents to support rigorous comparison against baseline
systems using quantifiable metrics such as recall, precision, ranking quality,
faithfulness, latency, and end-to-end correctness. The project will also
include failure analysis, A/B testing, security considerations such as
authentication, dataset isolation, and JWT, and a working citation-based demo
with documentation and a public URL where feasible.

---

## 25. Recommended Team Rule

If the system changes in a way that affects:

- evaluation design
- benchmark expectations
- demo scope
- security scope
- deployment scope
- report claims

update this document in the same batch as the code or planning change.
