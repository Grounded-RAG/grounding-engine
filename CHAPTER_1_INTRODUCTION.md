# Chapter One: Introduction

## 1.1 Background of the Study

The growth of digital information inside organizations has created a major knowledge-access challenge. Companies, institutions, agencies, research groups, and technical teams continuously produce documents such as policies, manuals, contracts, reports, specifications, standard operating procedures, meeting records, and internal guidelines. Although these documents contain valuable operational knowledge, users often struggle to find the exact information they need at the right time.

Traditional document access methods are limited. Manual browsing through folders is slow and repetitive. Keyword-based search helps only when the user already knows the exact wording used in the source document. In practice, many users ask broad, vague, or natural-language questions rather than exact keyword queries. This creates difficulty when organizations want fast, reliable, and easy access to knowledge stored in large document collections.

Large Language Models introduced a new way for users to interact with information. Instead of manually searching through documents, users can ask questions in natural language and receive direct answers. However, standalone LLMs are not enough for organizational use because they are not naturally grounded in an organization’s private documents. They may generate fluent but unsupported responses, combine internal facts with external model assumptions, and provide little evidence for why an answer should be trusted.

Retrieval-Augmented Generation emerged as an important solution to this limitation. A basic RAG system retrieves relevant text from a knowledge source and passes it to the language model before generation. This makes responses more grounded than standalone generation. However, basic RAG still has important weaknesses for real-world use. In particular, normal RAG often suffers from pipeline complexity, unreliable retrieval, and query ambiguity. These problems can lead to hallucination, weak evidence selection, low trust, and difficult deployment in production settings.

This project begins from that research problem. The study first examines why basic RAG is not sufficient for dependable organizational use. From that research understanding, it proposes an advanced or adaptive RAG pipeline that improves on normal RAG using a set of targeted methods: query transformation, semantic chunking, namespace isolation, hybrid retrieval, temporal ranking, reranking, corrective retrieval behavior, internal retrieval, verification, structured response enforcement, and source attribution.

The project then moves beyond research design alone. The advanced pipeline is used as the intelligence core of a real grounded AI platform built for organizations and users. Instead of requiring companies to build their own RAG systems from scratch, the product allows them to upload their documents, organize them into datasets, attach datasets to agents, ask questions through chat, inspect outputs, and manage access through a dashboard and API keys. In this way, the project has both a research contribution and a product contribution.

Therefore, the study is not only about proposing a stronger RAG pipeline. It is also about showing how that improved pipeline can be transformed into a usable software platform that makes grounded document intelligence easier, faster, and more trustworthy for real organizations.

## 1.2 Statement of the Problem

Basic Retrieval-Augmented Generation is useful because it grounds language-model answers in external documents instead of relying only on model memory. However, although this idea is promising, normal RAG still has major weaknesses when applied to practical organizational settings.

The first problem is **pipeline complexity**. A full RAG workflow requires multiple connected stages such as document ingestion, text extraction, chunking, embedding generation, indexing, retrieval, ranking, context packaging, answer generation, and response formatting. In many implementations, these parts are loosely connected and difficult to orchestrate reliably. This makes production deployment complex, especially for organizations that want document intelligence without building and maintaining the full technical stack themselves.

The second problem is **unreliable retrieval**. Basic RAG often depends too heavily on one retrieval method, especially vector similarity alone. As a result, it may return semantically related passages that are not truly answer-bearing, miss exact policy wording or identifiers, or surface outdated and contradictory information. When retrieval quality is weak, the generated answer also becomes weak, misleading, or incomplete.

The third problem is **query ambiguity**. Users often ask vague, underspecified, or multi-part questions. Basic RAG usually sends such queries directly into retrieval without first clarifying intent or decomposing the request. This causes the system to retrieve misaligned evidence and generate broad or generic responses that do not fully answer the real need of the user.

These three problems create a larger practical issue: basic RAG is often not trustworthy enough, not adaptive enough, and not easy enough to use as a serious organizational product. When query ambiguity, weak retrieval, and pipeline complexity are combined, the result is a higher risk of hallucination, poor evidence quality, and low user trust.

At the same time, organizations do not only need a research idea. They need a product that they can actually use. They need a system where users can upload company documents, organize them into manageable datasets, connect those datasets to reusable agents, ask grounded questions through a chat interface, inspect answers with evidence, and manage access safely and efficiently.

Therefore, the central problem addressed by this study is twofold:

1. how to improve basic RAG so that it becomes more adaptive, more grounded, more reliable, and more trustworthy
2. how to use that improved RAG design as the intelligence core of a real product for organizations and users

## 1.3 Objectives

The objectives of the study define both the research direction and the practical product outcome of the project.

### 1.3.1 General Objective

The general objective of this study is to design and implement a grounded AI platform that improves on basic RAG through an advanced or adaptive pipeline, and to use that improved pipeline to build a practical document-intelligence product for organizations and users.

### 1.3.2 Specific Objectives

The specific objectives of the study are to:

1. examine the weaknesses of basic RAG, especially pipeline complexity, unreliable retrieval, and query ambiguity
2. design an advanced or adaptive RAG pipeline that addresses these weaknesses using targeted retrieval and verification methods
3. implement agentic query transformation to reduce ambiguity before retrieval
4. implement semantic chunking to preserve document meaning more effectively during indexing
5. implement namespace isolation to support secure organizational data separation
6. implement hybrid retrieval that combines keyword precision and semantic depth
7. implement temporal ranking to reduce the impact of outdated information
8. implement reranking to improve final evidence quality
9. implement corrective retrieval behavior when support is weak or confidence is low
10. implement verification-oriented answer generation with structured enforcement and source attribution
11. build a product that allows users to upload documents and organize them into datasets
12. build agent workflows so that datasets can be attached to reusable grounded assistants
13. build a chat-based interface for grounded interaction with uploaded knowledge
14. build dashboard and run-inspection features for visibility, management, and traceability
15. provide developer and organizational access through API keys and product workflows
16. evaluate both the advanced pipeline behavior and the practical usability of the final platform

## 1.4 Scope and Limitation

### 1.4.1 Scope of the Study

The scope of this study includes both the research-side grounding pipeline and the product-side platform built around it.

From the research and technical side, the scope includes the design and implementation of an advanced RAG pipeline that improves on basic RAG through the following major methods:

- query transformation
- semantic chunking
- namespace isolation
- hybrid retrieval
- temporal ranking
- reranking
- corrective retrieval behavior
- internal retrieval support
- verification loop
- structured enforcement
- source attribution

From the product side, the scope includes the design and implementation of a usable grounded AI platform in which organizations and users can:

- create workspaces
- create and manage datasets
- upload TXT, PDF, and DOCX documents
- process those documents into searchable grounded knowledge
- create grounded agents connected to datasets
- use a chat page to ask questions over organizational knowledge
- receive grounded answers with citations and trust signals
- inspect runs and outputs through product pages
- manage API keys and system access

The study therefore covers both the internal intelligence pipeline and the external user-facing software platform that makes the pipeline practical for real use.

### 1.4.2 Limitation of the Study

Although the project delivers a complete academic and product-oriented system within its defined boundary, the study has several limitations.

1. document ingestion is focused on text-oriented formats such as TXT, PDF, and DOCX
2. answer quality depends on the quality, relevance, and completeness of the uploaded organizational corpus
3. highly ambiguous or underspecified questions may still need clarification despite improved query handling
4. retrieval quality remains influenced by document structure and source consistency
5. very large-scale enterprise deployment optimization is outside the academic scope of the study
6. broader third-party source connectors and deeper enterprise governance features are beyond the current study boundary

## 1.5 Methodology

The study followed a software engineering research-and-development methodology. The approach was both analytical and constructive. First, it analyzed a real problem in basic RAG and document intelligence. Then it designed an improved pipeline to solve that problem. Finally, it implemented the pipeline as part of a complete software platform.

### 1.5.1 Research and Design Approach

The project began by studying the limitations of basic RAG, standalone LLM use, and traditional document-access workflows. This analysis showed that the main weaknesses were pipeline complexity, unreliable retrieval, and query ambiguity. Based on this understanding, the study defined an advanced adaptive pipeline intended to improve trust, retrieval quality, and practical usability.

### 1.5.2 Product-Oriented Development Approach

After defining the improved pipeline, the project translated the research outcome into a usable product. This required more than retrieval design alone. It required product structures such as datasets, uploads, agents, conversations, chat workflows, dashboard visibility, access control, and run inspection. In other words, the project moved from RAG research into complete product engineering.

### 1.5.3 Development Method

The implementation process followed these major stages:

1. problem identification and research framing
2. literature review and method selection
3. requirement analysis for both the pipeline and the product
4. design of the advanced RAG pipeline
5. design of the product architecture and data model
6. implementation of ingestion, retrieval, grounding, and verification services
7. implementation of datasets, agents, chat, dashboard, and API workflows
8. testing and evaluation of both the technical pipeline and the user-facing platform
9. final report and documentation preparation

### 1.5.4 Technologies and Standards Used

The system was implemented using FastAPI for backend services, React and TypeScript for the frontend, PostgreSQL for structured storage and sparse retrieval support, Qdrant for dense vector retrieval, MinIO for object storage, and Docker Compose for reproducible infrastructure. Testing and validation relied on route inspection, workflow verification, service behavior analysis, and run-trace evaluation.

## 1.6 Plan of Activities

The study followed a structured progression from research problem analysis to final system delivery.

### Table 1.1. Plan of Activities

| No. | Activity | Description | Deliverable |
|---|---|---|---|
| 1 | Problem identification | identify weaknesses in basic RAG and document access | problem definition |
| 2 | Literature review | review RAG, retrieval, verification, and adaptive methods | literature review chapter |
| 3 | Requirement analysis | define research and product requirements | requirement specification |
| 4 | System modeling | model pipeline behavior and product workflows | analysis and modeling chapter |
| 5 | System design | design adaptive pipeline and product architecture | design chapter |
| 6 | Backend implementation | implement ingestion, retrieval, grounding, and APIs | working backend |
| 7 | Frontend implementation | implement datasets, agents, chat, runs, and dashboard | working frontend |
| 8 | Evaluation | test technical behavior and product workflows | evaluation chapter |
| 9 | Documentation | prepare final academic and technical report | final report |

## 1.7 Budget Required

The project was implemented mainly with software tools, open-source frameworks, and local computing resources.

### Table 1.2. Estimated Budget Required

| No. | Item | Purpose | Estimated Cost (ETB) |
|---|---|---|---|
| 1 | Internet access | package downloads, documentation, testing resources | 3,000 |
| 2 | Power and computing use | development and infrastructure runtime | 2,500 |
| 3 | Printing and binding | proposal, drafts, final report submission | 2,000 |
| 4 | Stationery | notebooks, pens, review materials | 800 |
| 5 | Contingency | miscellaneous technical and reporting costs | 1,700 |
|  |  | **Total Estimated Budget** | **10,000 ETB** |

## 1.8 Significance of the Study

This study is significant because it contributes at both the research level and the product level.

From the research perspective, the study addresses an important weakness in basic RAG. It shows that simply retrieving a few passages and passing them to a language model is not enough for dependable organizational use. It demonstrates the need for a more adaptive and verification-aware pipeline that improves retrieval quality, reduces ambiguity, and increases trust.

From the product perspective, the study shows how advanced RAG ideas can be transformed into a real platform. Rather than expecting organizations to build and orchestrate their own document-intelligence stack, the system provides a practical software environment where they can upload knowledge, structure it into datasets, connect it to agents, and interact with it through grounded chat and inspection workflows.

The study is significant in the following ways:

1. it clearly identifies major weaknesses in basic RAG for real-world organizational use
2. it proposes an advanced adaptive pipeline as a research contribution
3. it transforms that pipeline into a practical grounded AI product
4. it reduces the difficulty of using RAG for organizations by shifting complexity into the platform
5. it improves trust through citations, verification, and source attribution
6. it demonstrates how research-driven AI system design can become a usable software product

## 1.9 Outline of the Study

This report is organized into seven chapters.

### Chapter One: Introduction

This chapter presents the background of the study, the problem statement, objectives, scope and limitations, methodology, plan of activities, budget, significance, and report structure. It introduces both the research problem in basic RAG and the product vision of Grounded AI.

### Chapter Two: Literature Review

This chapter reviews the concepts, methods, and related works relevant to the study. It explains basic RAG, its weaknesses, and the techniques used to improve it. It also provides the theoretical foundation for the advanced adaptive pipeline.

### Chapter Three: Problem Analysis and Modeling

This chapter analyzes the real problem from both technical and practical viewpoints. It defines the weaknesses of existing approaches, the needs of organizations and users, and the requirements of the proposed solution.

### Chapter Four: System Design

This chapter presents the design of the advanced pipeline and the design of the product built around it. It explains how the intelligence core connects with datasets, agents, chat, dashboard workflows, and organizational access.

### Chapter Five: System Implementation

This chapter explains how the system was built in practice. It covers the implementation of the grounding pipeline and the implementation of the user-facing product features.

### Chapter Six: System Evaluation

This chapter evaluates both sides of the work: the behavior of the improved RAG pipeline and the usability of the final software platform.

### Chapter Seven: Conclusions and Recommendations

This chapter concludes the study by summarizing the major findings, restating the research and product contributions, and providing recommendations for future work.

## 1.10 Chapter Summary

This chapter introduced the study by establishing a clear story. The work begins from a research problem: basic RAG is useful but still has major weaknesses for real-world use, especially pipeline complexity, unreliable retrieval, and query ambiguity. The study responds by designing an advanced adaptive pipeline to improve basic RAG. It then uses that improved pipeline as the intelligence core of a real grounded AI platform for organizations and users. The next chapter reviews the literature and related works that support this direction.
