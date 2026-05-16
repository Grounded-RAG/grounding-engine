# Chapter Two: Literature Review

## 2.1 Overview of the Literature Review

This chapter reviews the main concepts and related works that informed Grounded AI. The literature is examined from two connected perspectives. The first perspective is the research side: how to improve grounding quality, retrieval reliability, answer traceability, and ambiguity handling in RAG systems. The second perspective is the product side: how document AI systems are packaged into usable workflows for organizations, teams, and end users.

The goal of the review is not to treat Grounded AI as only a research pipeline or only a software dashboard. Instead, the review explains why both are necessary. A strong product without a trustworthy grounding engine produces weak answers. A strong retrieval idea without a usable product is difficult for organizations to adopt.

## 2.2 Study Related Works

### 2.2.1 Large Language Models

Large Language Models are capable of natural-language interaction, summarization, explanation, and question answering. They have changed user expectations by making conversational interfaces normal. In organizational settings, this creates demand for systems where users can ask direct questions rather than navigating complex file repositories.

However, standalone LLMs are not enough for organizational document use. They may generate unsupported information, blend external training knowledge with internal facts, and fail to identify whether a statement came from a specific source document. This makes them risky in business, technical, compliance, and research environments.

### 2.2.2 Retrieval-Augmented Generation

Retrieval-Augmented Generation connects a generator with an external document corpus. Instead of answering only from model memory, the system retrieves evidence and uses that evidence during response generation. This makes RAG suitable for private datasets, changing documents, and organization-specific knowledge.

RAG is attractive because it allows teams to use their own data without retraining a foundation model. For a product like Grounded AI, this is essential because organizations need to upload and use their own knowledge collections directly.

### 2.2.3 Traditional RAG Limitations

Basic RAG is useful but often incomplete. A common baseline flow is document chunking, embedding generation, vector retrieval, and answer generation. While this approach works as a prototype, it has several limitations in practice:

1. it is technically complicated for many organizations to build and maintain
2. vector-only retrieval can return evidence that is related but not precise
3. vague queries are not handled well
4. answer grounding may be weak even when retrieval exists
5. many systems provide little visibility into why a response was produced

These limitations are directly relevant to Grounded AI because the project aims to reduce complication for the user while improving internal answer quality.

### 2.2.4 Hybrid Retrieval

Hybrid retrieval combines lexical search and semantic search. Lexical search is strong for exact wording, identifiers, policy names, and structured terms. Semantic search is strong for paraphrase and conceptual similarity. In organizational data, both are needed. Users often ask natural questions, but documents may still contain exact terminology that matters.

This makes hybrid retrieval especially important for business use because organizational questions can range from exact compliance wording to broad explanatory prompts.

### 2.2.5 Lexical Retrieval and Full-Text Search

Lexical retrieval methods such as BM25 and full-text search remain valuable in document systems. Even in modern AI products, exact term retrieval is still important for technical documents, legal wording, version references, names, and section titles. A system designed for organizational use should not abandon lexical precision simply because semantic search exists.

### 2.2.6 Semantic Search and Vector Databases

Semantic search represents text as embeddings and retrieves passages based on meaning rather than exact words. Vector databases make this practical at scale. This is one of the key foundations of modern RAG products. At the same time, semantic similarity alone does not guarantee answer relevance, which is why later stages such as reranking and verification are important.

### 2.2.7 Reciprocal Rank Fusion

Reciprocal Rank Fusion is a practical method for combining results from multiple retrieval strategies. It is especially useful when a system wants to preserve both lexical precision and semantic depth. In a product-oriented platform, this helps keep retrieval strong across many user question styles.

### 2.2.8 Reranking

Reranking improves the final evidence set after first-pass retrieval. It helps a system decide which among the retrieved candidates are most likely to support the answer directly. This is important because organizational users care about getting the right answer quickly, not just a large pool of possibly relevant snippets.

### 2.2.9 Temporal Awareness in Retrieval

Many organizational datasets change over time. Policies are updated, procedures are revised, and technical documents are versioned. Without temporal awareness, a system may surface old content that is no longer the best source. Temporal scoring therefore matters in any product intended for practical organizational use.

### 2.2.10 Query Ambiguity and Query Transformation

Real users often ask broad or underspecified questions. Query transformation techniques try to clarify or decompose these questions before retrieval. This is especially useful in enterprise knowledge systems because users may know the problem they want solved but not the document language that contains the answer.

### 2.2.11 Trust, Verification, and Grounded Answering

Research in trustworthy RAG increasingly emphasizes that retrieval alone is not enough. Systems need mechanisms for checking evidence strength, surfacing uncertainty, attaching citations, and avoiding unsupported claims. These ideas shaped the verification-aware parts of Grounded AI.

### 2.2.12 Product-Oriented Knowledge Systems

Many academic discussions stop at retrieval and generation. However, usable organizational systems require more. A real product needs dataset management, upload workflows, agents or assistants, chat interfaces, trace inspection, and access control. These product features are not separate from grounding quality. They shape whether the system is usable, governable, and adoptable.

### 2.2.13 Agents in Organizational AI Products

Agents act as reusable assistants configured with instructions and attached knowledge sources. For organizations, this is useful because one team may want a policy assistant, another may want a technical support assistant, and another may want a project knowledge assistant. Dataset-attached agents provide a structured way to reuse knowledge over time.

### 2.2.14 Datasets as Knowledge Boundaries

Datasets are important not only as storage containers but as knowledge boundaries. They define which documents belong together for retrieval and answering. In product terms, datasets give users a manageable unit for uploading, organizing, and governing content. In retrieval terms, they reduce irrelevant search scope and improve answer focus.

### 2.2.15 Chat Interfaces for Grounded Question Answering

Chat interfaces have become the most natural way for users to interact with AI systems. In a grounded document platform, chat should not be a simple prompt box. It should be connected to an agent, backed by selected datasets, and supported by traceable runs and citations. This product perspective is central to the system implemented in this study.

## 2.3 Milestones and Gaps in Related Works

The reviewed literature and practical systems reveal several milestones.

### 2.3.1 Milestone One: Conversational AI Interfaces

Users became comfortable asking natural-language questions through chat-like interfaces.

### 2.3.2 Milestone Two: External Knowledge Grounding

RAG enabled answers to be based on external corpora rather than only model memory.

### 2.3.3 Milestone Three: Hybrid and Multi-Stage Retrieval

The field recognized that stronger retrieval requires combining methods rather than relying on one search strategy.

### 2.3.4 Milestone Four: Trust-Aware Answer Design

Verification, citations, and grounded response shaping became more important as systems moved closer to practical use.

### 2.3.5 Milestone Five: Productization of Document AI

Document AI evolved from demos toward product workflows with uploads, datasets, assistants, dashboards, and governance features.

### 2.3.6 Gaps Identified

Despite these milestones, important gaps remain:

1. many systems are still too research-oriented and not packaged as usable organizational products
2. many product experiences still rely on weak or opaque grounding pipelines
3. many RAG systems are difficult for companies to deploy and operate
4. many systems do not clearly separate document collections into manageable dataset boundaries
5. many systems do not support reusable agents over attached knowledge collections
6. many systems provide answers but not sufficiently clear run inspection and traceability

Grounded AI is positioned as a response to these gaps by combining a grounded pipeline with product workflows for datasets, agents, chat, and operational inspection.

## 2.4 Lessons Learned from the Literature

The literature review produced several key lessons.

1. organizations need grounded AI systems, not standalone generative models
2. product adoption depends on ease of use, not only on algorithmic quality
3. dataset structure and retrieval boundaries are central to answer quality
4. agents are useful abstractions for reusable organizational assistants
5. chat is the dominant user interaction model, but it must be backed by citations and traceability
6. trust must be designed into the system architecture rather than added later
7. reducing RAG setup complexity is itself an important practical contribution

## 2.5 Chapter Summary

This chapter reviewed the theories and practical systems that informed Grounded AI. It showed that the project is shaped by both grounded AI research and product-design needs. The review supports a platform in which organizations can upload knowledge, form datasets, attach them to agents, and interact through chat, while a stronger retrieval and verification engine works behind the scenes to improve answer quality.
