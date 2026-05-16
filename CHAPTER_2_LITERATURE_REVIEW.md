# Chapter Two: Literature Review

## 2.1 Overview of the Literature Review

This chapter reviews the major concepts, methods, and related works that informed the design of Grounded AI. The purpose of the review is not only to describe Retrieval-Augmented Generation in general, but also to explain why improving basic RAG is necessary for real-world organizational use.

The project begins from a clear research position: basic RAG is valuable, but it still has major weaknesses when applied to serious document-intelligence tasks. In particular, basic RAG often struggles with pipeline complexity, unreliable retrieval, and query ambiguity. These weaknesses make it difficult to use ordinary RAG as a dependable product for organizations.

For that reason, the literature review focuses on two connected questions:

1. what are the limitations of basic RAG and related document-answering systems?
2. what methods can be combined to design a stronger adaptive pipeline for grounded organizational use?

This chapter therefore reviews both the weaknesses of standard approaches and the advanced methods that informed the final system.

## 2.2 Study Related Works

### 2.2.1 Large Language Models

Large Language Models have transformed the way users interact with digital systems. They are highly effective in text generation, summarization, dialogue, reasoning, translation, and explanation. Their main advantage is that they let users communicate with software through natural language instead of rigid command syntax.

However, LLMs alone are not sufficient for organizational knowledge access. They are trained on broad corpora and are not inherently tied to a specific organization’s private documents. As a result, they may generate answers that sound fluent and convincing but are not actually grounded in the user’s own data. This creates a major trust problem for settings where accuracy and evidence matter.

### 2.2.2 Retrieval-Augmented Generation

Retrieval-Augmented Generation combines retrieval and generation. Instead of asking the model to answer entirely from its internal memory, the system first retrieves relevant external evidence and then uses that evidence during generation. This makes RAG especially useful when the knowledge source is private, changing over time, or too specific to be fully represented in the model’s training data.

RAG is therefore highly relevant for organizations that want to ask questions over internal documents, policies, manuals, and technical records.

### 2.2.3 Basic RAG

Basic RAG usually follows a simple process:

1. ingest documents
2. split them into chunks
3. embed the chunks
4. store them in a vector database
5. embed the user query
6. retrieve top-k chunks
7. pass those chunks to the language model
8. generate the answer

This design is useful as a starting point because it reduces dependence on model memory and introduces external grounding. However, the literature and practice both show that this standard pattern is often not enough for real organizational use.

### 2.2.4 Weaknesses of Basic RAG

The most important literature finding for this study is that basic RAG has serious limitations when moved from prototype use to dependable product use.

#### Pipeline Complexity

Basic RAG seems simple at a high level, but in practice it includes many connected tasks: ingestion, extraction, chunking, indexing, retrieval, ranking, context building, answer generation, and output handling. These parts are often implemented as loosely connected components. This creates operational complexity and makes production-quality deployment difficult.

#### Unreliable Retrieval

Basic RAG often depends too heavily on one retrieval path, especially dense vector similarity. This can cause the system to return passages that are semantically related but not directly answer-bearing. It may also struggle with exact policy wording, identifiers, names, version labels, or date-sensitive content. When retrieval is weak, answer quality also becomes weak.

#### Query Ambiguity

Users do not always ask precise questions. They may ask broad, vague, comparative, or multi-part questions. Basic RAG often sends such queries directly to retrieval without any deeper interpretation. This leads to evidence misalignment and generic responses.

#### Hallucination and Weak Trust

When retrieval is incomplete, misaligned, or weak, generation may still proceed confidently. This can produce hallucinated or partially supported responses. If the system also lacks clear citations and verification controls, users may have no reliable way to know whether an answer should be trusted.

These weaknesses are central to this study because they define the exact gap that the project tries to solve.

### 2.2.5 Hybrid Retrieval

Hybrid retrieval combines lexical search and semantic search. Lexical search is effective for exact terms, identifiers, names, and policy wording. Semantic search is effective for paraphrase, related concepts, and broader meaning. Since organizational questions can require either exact matching or semantic understanding, hybrid retrieval is often stronger than using only one retrieval method.

This literature is important because it directly supports the project’s effort to improve retrieval reliability.

### 2.2.6 BM25 and Lexical Retrieval

BM25 and related lexical retrieval methods remain strong baselines in information retrieval. They are especially effective when exact wording matters. Even though many modern AI systems emphasize embeddings and vectors, lexical retrieval remains important for grounded organizational tasks.

This supports the design decision to avoid dependence on vector retrieval alone.

### 2.2.7 Semantic Search

Semantic search retrieves information based on meaning rather than exact keyword overlap. This is useful when users paraphrase concepts or ask broader natural-language questions. However, semantic similarity alone is not always enough. It can retrieve content that is topically related without being the best evidence for a specific answer.

Therefore, semantic search is most effective when combined with lexical search and stronger downstream ranking logic.

### 2.2.8 Reciprocal Rank Fusion

Reciprocal Rank Fusion is a practical technique for combining ranked lists from multiple retrieval methods. Instead of requiring all methods to share one scoring scale, it uses rank positions. This makes it suitable for combining sparse and dense retrieval outputs in a robust way.

RRF is important to this study because it helps merge lexical precision and semantic depth into one stronger retrieval stage.

### 2.2.9 Reranking

Reranking improves the order of retrieved evidence after the first retrieval pass. Initial retrieval is often good for building a candidate pool, but not always good enough for selecting the final best evidence. Reranking applies deeper relevance judgment and helps the system identify which passages truly deserve to be shown to generation.

This is directly connected to solving unreliable retrieval.

### 2.2.10 Temporal Ranking and Freshness-Aware Retrieval

In many document environments, newer information is more correct than older information. Policies are updated, procedures change, versions evolve, and technical guidance becomes outdated. If retrieval ignores time, older but no longer accurate content may be selected.

Temporal ranking helps address this issue by incorporating freshness into retrieval decisions. This supports the project’s goal of reducing unreliable retrieval.

### 2.2.11 Query Transformation

Query transformation methods aim to improve retrieval by reformulating, clarifying, or decomposing the user request before search. This is especially important when queries are vague, broad, or multi-part.

For this study, query transformation is one of the most important methods because it directly addresses query ambiguity. Instead of assuming that the first user phrasing is optimal for retrieval, the system can transform the request into more retrieval-friendly forms.

### 2.2.12 Semantic Chunking

Chunking is one of the most important design choices in RAG systems. Simple fixed-size chunking is easy to implement, but it can split ideas at unnatural boundaries and weaken context. Semantic chunking aims to preserve logical meaning by splitting at topic boundaries or structural transitions.

This supports better retrieval because the stored evidence units are more coherent and meaningful.

### 2.2.13 Corrective RAG

Corrective RAG introduces the idea that retrieval should not be treated as automatically sufficient. If the first evidence set is weak, contradictory, or low-confidence, the system should attempt additional corrective behavior rather than blindly continuing. This may include retrying, reformulating, or gathering stronger evidence.

This idea is important because it treats weak retrieval as a problem to be handled actively, not passively.

### 2.2.14 Internal Retrieval and Long-Context Reading

Some questions require more than small chunk-level context. In such cases, internal long-context reading can help the system examine larger bodies of text and improve recall. This is useful when the best answer depends on broader context that may not be visible in one small chunk.

### 2.2.15 Verification-Oriented Answering

Verification-oriented approaches recognize that answer generation should not be treated as the final unquestioned step. Instead, the system should evaluate whether the produced answer is well supported by the selected evidence. Verification can include claim checking, contradiction detection, support classification, and confidence shaping.

This is essential for reducing hallucination and increasing trust.

### 2.2.16 Structured Output and Source Attribution

Trustworthy organizational AI systems should not only answer questions. They should also show why the answer should be trusted. Structured output helps make answers consistent and inspectable. Source attribution links claims back to the supporting evidence.

These methods are important because they make grounded answering auditable rather than opaque.

### 2.2.17 Agent-Oriented Grounded Interaction

Organizations often need more than a single query box. They may need reusable assistants that are configured for specific knowledge domains, roles, or tasks. Agent-oriented grounded interaction allows datasets to be attached to named assistants, making knowledge access more structured and reusable.

This directly supports the product side of the study, where users create agents connected to datasets.

### 2.2.18 Productized Document Intelligence Platforms

Related practical systems show that organizations need more than a good retrieval pipeline. They need complete workflows: upload, dataset formation, document management, chat interaction, visibility into runs, and controlled access. A RAG pipeline alone is not a product. It becomes practically useful only when embedded inside a usable platform.

This literature is important because it supports the product contribution of the project.

## 2.3 Identifying Milestones of Related Literature and Finding the Gaps

The reviewed literature shows a progression in the development of grounded AI systems.

### 2.3.1 Milestone One: Standalone LLM Interfaces

The first major milestone was the rise of conversational interfaces built directly on large language models. These systems changed expectations about how users interact with software, but they lacked grounding in private organizational documents.

### 2.3.2 Milestone Two: Basic Vector-Based RAG

The second milestone was the adoption of basic RAG, where external evidence was retrieved before answer generation. This improved over standalone LLM use, but still left major weaknesses unresolved.

### 2.3.3 Milestone Three: Hybrid Retrieval and Better Ranking

The third milestone was recognition that retrieval quality could be improved through hybrid search and reranking. This made evidence selection stronger than simple top-k vector retrieval.

### 2.3.4 Milestone Four: Adaptive and Corrective Retrieval Methods

The fourth milestone was the emergence of techniques such as query transformation, corrective behavior, temporal awareness, and stronger evidence handling.

### 2.3.5 Milestone Five: Trust-Oriented and Productized Grounded Systems

The fifth milestone was the move toward systems that emphasize verification, citations, inspectability, and product workflows rather than only retrieval experiments.

### 2.3.6 Gaps Identified in the Literature and Practice

Despite these advances, several important gaps remain.

1. many systems still use basic RAG patterns without solving pipeline complexity fully
2. many systems still rely too heavily on one retrieval mode and therefore suffer from unreliable evidence selection
3. many systems do not handle ambiguous user queries well before retrieval
4. many systems provide answers without sufficiently strong verification and attribution controls
5. many works focus on research methods without turning them into practical organizational products
6. many products provide surface-level AI chat but do not expose the deeper grounded pipeline clearly and reliably

These gaps justify the need for Grounded AI.

## 2.4 Lessons Learned from Literature

Several major lessons from the literature shaped the system.

### 2.4.1 Basic RAG Is a Starting Point, Not the Final Answer

The literature shows that basic RAG is useful but incomplete. It should be improved rather than adopted without modification.

### 2.4.2 Retrieval Quality Determines Answer Quality

If the retrieval stage is weak, answer quality becomes weak. Strong generation alone cannot fix bad evidence selection.

### 2.4.3 Query Handling Must Happen Before Retrieval

Ambiguous or broad user questions should not be passed directly to retrieval without interpretation.

### 2.4.4 Trust Requires More Than Retrieval

Trustworthy grounded systems require citations, structured responses, verification, and inspectability.

### 2.4.5 A Good Pipeline Is Not Enough Without a Good Product

Organizations do not only need a technically improved RAG method. They need a system where the improved method is accessible through datasets, agents, uploads, chat, dashboards, and manageable workflows.

## 2.5 Chapter Summary

This chapter reviewed the literature and related works that informed the study. It explained Large Language Models, Retrieval-Augmented Generation, the weaknesses of basic RAG, hybrid retrieval, lexical and semantic search, fusion, reranking, temporal ranking, query transformation, semantic chunking, corrective retrieval, verification, structured output, and productized document intelligence. The review shows that the project is grounded in a clear research gap: basic RAG is useful but insufficient for dependable organizational use. This directly motivates the study’s research contribution, namely an advanced adaptive RAG pipeline, and its product contribution, namely a grounded AI platform built around that pipeline.
