# Chapter Three: Problem Analysis and Modeling

## 3.1 Overview

This chapter translates the research problem and product goal of the study into a structured system analysis. The project does not address only one issue. It addresses two connected realities.

The first reality is the research problem: basic RAG is useful, but still weak for dependable real-world use because of pipeline complexity, unreliable retrieval, and query ambiguity.

The second reality is the product problem: organizations need a usable software platform, not only a research pipeline. They need a system where they can upload their own data, organize it into datasets, attach datasets to agents, ask questions through chat, and trust the resulting answers.

This chapter therefore analyzes both the technical and practical problem context, identifies the affected stakeholders, specifies the required solution characteristics, and models the final system from functional, non-functional, and behavioral perspectives.

## 3.2 Existing System and Its Problems

### 3.2.1 Existing System Landscape

Before the proposed solution, document-intelligence needs were commonly addressed through one or more of the following approaches:

1. manual browsing through folders and repositories
2. keyword-based search in file systems or portals
3. static document repositories without intelligent question answering
4. standalone LLM chat systems disconnected from organizational documents
5. basic RAG prototypes that retrieve a small set of chunks and generate answers directly

Each of these approaches helps in some limited way, but none fully solves the combined need for grounded intelligence, practical usability, traceability, and trust.

### 3.2.2 Problems in Traditional Document Access

Manual browsing and document search are time-consuming and inefficient. Users often open many files, scan long sections, compare multiple versions, and try to piece together the answer themselves. Keyword search helps only when the user already knows the exact terms used in the document. These approaches do not provide direct grounded answers and place a heavy cognitive burden on users.

### 3.2.3 Problems in Standalone LLM Use

Standalone LLMs make interaction easier because they accept natural-language questions, but they do not naturally know the organization’s private documents. This creates major risks:

- answers may be based on general model memory rather than internal evidence
- responses may be confident even when unsupported
- no strong citation linkage exists between answer and source
- users cannot easily inspect how the answer was formed

### 3.2.4 Problems in Basic RAG

Basic RAG improves on standalone LLMs by retrieving evidence from a corpus before answer generation. However, for real organizational use, basic RAG still has three major weaknesses.

#### Problem 1: Pipeline Complexity

Basic RAG is often described as simple, but in practice it involves many connected components:

- upload and ingestion
- extraction
- chunking
- embeddings
- vector database indexing
- sparse or lexical search support
- retrieval orchestration
- ranking
- answer generation
- formatting and citation output

When these parts are weakly integrated, organizations face significant complexity in building, deploying, and maintaining the pipeline. This makes basic RAG hard to use as a dependable product.

#### Problem 2: Unreliable Retrieval

Retrieval quality is one of the most important determinants of grounded answer quality. Basic RAG often retrieves only by dense similarity or simple top-k logic. This can produce several failures:

- semantically related but non-answer-bearing passages
- weak exact matching for identifiers and policy wording
- outdated evidence being selected over fresher evidence
- contradictory chunks being included without resolution

When retrieval is unreliable, the answer becomes unreliable as well.

#### Problem 3: Query Ambiguity

Users often ask vague, broad, conversational, or multi-part questions. Basic RAG commonly sends these directly into retrieval without enough interpretation. This creates mismatch between what the user means and what the system retrieves. As a result, the answer may be generic, incomplete, or misaligned with the real need.

#### Resulting Issue: Hallucination and Weak Trust

When pipeline complexity, retrieval weakness, and ambiguity interact, hallucination risk increases. Even if the system sounds fluent, users may not know whether the answer is truly supported. This weakens trust and reduces the usefulness of the system in organizational settings.

### 3.2.5 Product-Side Problems for Organizations

Even if a technically strong retrieval pipeline exists, organizations still face product-level problems if the system is not packaged in a usable way. Common gaps include:

- no clear dataset structure for uploaded knowledge
- no reusable grounded agents for repeated tasks
- no chat workflow for natural interaction
- no visibility into runs and outputs
- no simple developer access model
- too much setup complexity for teams that only want to use the system

This means the problem is not only improving RAG. It is also delivering RAG as a usable product.

### 3.2.6 Stakeholders Affected by the Problems

The identified problems affect several groups.

#### End Users

They need quick, reliable, grounded answers from organizational data but often receive slow search experiences or weak AI responses.

#### Organizations and Teams

They want a system they can use without building a complete RAG pipeline from scratch.

#### Knowledge Managers

They need document collections to be organized into manageable datasets and kept ready for retrieval.

#### Agent Builders and Analysts

They need reusable assistants tied to datasets, with inspectable outputs and grounded behavior.

#### Developers and Integrators

They need secure programmatic access through APIs and keys, without excessive infrastructure complexity.

#### Administrators

They need safe organizational separation, controlled access, and operational visibility.

### 3.2.7 Impact of the Problems

The problems identified above lead to several practical consequences:

- reduced efficiency in finding organizational knowledge
- lower trust in AI-generated responses
- increased risk of unsupported decisions
- technical difficulty in deploying document-intelligence systems
- poor visibility into how answers were produced
- weaker adoption of grounded AI inside organizations

## 3.3 Specifying the Requirements of the Proposed Solution

### 3.3.1 Requirement Elicitation Approach

Requirements were derived from the research problem, the target product vision, the proposal materials, the architecture direction, and the implemented product workflows. The requirement analysis therefore considered both the intelligence core and the user-facing platform.

### 3.3.2 High-Level Solution Direction

The proposed solution must satisfy two major expectations:

1. it must improve on basic RAG by solving pipeline complexity, unreliable retrieval, and query ambiguity
2. it must present that improved intelligence through a real product that organizations and users can operate easily

### 3.3.3 Stakeholder Requirements Summary

#### End Users Require

- natural-language interaction through chat
- grounded answers with citations
- low-friction access to organizational knowledge
- visibility into whether the answer is trustworthy

#### Organizations Require

- simple document upload and knowledge organization
- reusable dataset structures
- agents that can be attached to relevant knowledge collections
- reduced complexity compared with building RAG internally

#### Knowledge Operators Require

- dataset creation and management
- upload handling
- document readiness visibility
- ingestion monitoring

#### Agent Builders Require

- agent creation and update
- dataset attachment
- reusable instructions and interaction contexts

#### Developers Require

- stable APIs
- API key access
- inspectable run outputs
- integration-friendly system behavior

#### Administrators Require

- tenant and workspace isolation
- controlled access boundaries
- revocable credentials
- operational oversight

## 3.4 System Modeling

### 3.4.1 Functional Requirements

The functional requirements define what the final system shall do.

#### Advanced Pipeline Requirements

1. the system shall analyze user queries before retrieval
2. the system shall transform vague or broad queries into better retrieval-oriented forms when needed
3. the system shall chunk documents in a way that preserves semantic coherence
4. the system shall isolate organizational data through namespace or tenant-scoped structures
5. the system shall perform hybrid retrieval using lexical and semantic methods
6. the system shall apply freshness-aware or temporal ranking when appropriate
7. the system shall rerank retrieved candidates before generation
8. the system shall support corrective retrieval behavior when support is weak
9. the system shall support deeper internal retrieval when broader context is needed
10. the system shall generate grounded answers from selected evidence
11. the system shall verify or assess support quality before final answer delivery
12. the system shall return structured outputs with source attribution

#### Product Workflow Requirements

13. the system shall allow workspace creation and management
14. the system shall allow dataset creation, listing, retrieval, and update
15. the system shall allow users to upload TXT, PDF, and DOCX files into datasets
16. the system shall process uploaded documents into searchable evidence
17. the system shall allow agent creation and update
18. the system shall allow datasets to be attached to agents
19. the system shall support conversation-based grounded chat
20. the system shall persist messages and runs
21. the system shall provide dashboard summaries and recent activity visibility
22. the system shall support API key creation and revocation
23. the system shall allow run inspection with citations, routing, and trust metadata

### 3.4.2 Non-Functional Requirements

The non-functional requirements define the desired quality attributes.

#### Reliability

The system shall produce answers that are more dependable than basic RAG through stronger retrieval and trust controls.

#### Usability

The system shall be usable by organizations and users without requiring them to build their own RAG stack.

#### Security

The system shall isolate resources by tenant, workspace, and dataset ownership rules.

#### Traceability

The system shall preserve enough execution data to explain how grounded answers were produced.

#### Performance

The system shall support practical query response time through indexed retrieval and controlled execution depth.

#### Maintainability

The system shall separate concerns clearly across services, APIs, and infrastructure components.

#### Extensibility

The system shall support future improvements in retrieval, verification, providers, and organizational workflows.

### 3.4.3 Use Case

#### Actors of the System

The main actors are:

1. visitor
2. authenticated user
3. workspace operator
4. agent builder
5. developer or API client
6. administrator
7. background ingestion worker

#### Major Use Cases

The major use cases are:

1. register and sign in
2. create workspace
3. create dataset
4. upload documents into dataset
5. monitor ingestion progress
6. create grounded agent
7. attach dataset to agent
8. create or continue conversation
9. ask grounded question through chat
10. inspect run output and trace details
11. create API key
12. revoke API key

#### Use Case Description 1: Upload Organizational Knowledge

- Primary actor: Workspace Operator
- Precondition: authenticated user with a workspace
- Main success scenario:
1. user opens the dataset page
2. user creates or selects a dataset
3. user uploads one or more documents
4. system validates and stores the files
5. system creates document and ingestion records
6. background processing converts them into searchable grounded knowledge
- Postcondition: organizational knowledge becomes queryable through the system

#### Use Case Description 2: Create Grounded Agent

- Primary actor: Agent Builder
- Precondition: workspace exists and at least one dataset is available
- Main success scenario:
1. user creates an agent
2. user defines the agent name and instructions
3. user attaches one or more datasets
4. system stores the configuration
- Postcondition: reusable grounded assistant becomes available

#### Use Case Description 3: Ask Question Through Chat

- Primary actor: Authenticated User
- Precondition: conversation exists and an agent or dataset scope is available
- Main success scenario:
1. user enters a natural-language question in the chat page
2. system analyzes the query
3. system performs improved retrieval and grounded generation
4. system returns answer with citations and trust information
5. system persists messages and run data
- Postcondition: user receives a grounded response and the interaction becomes inspectable

#### Use Case Description 4: Inspect Answer Run

- Primary actor: Authenticated User
- Precondition: at least one run exists
- Main success scenario:
1. user opens the runs page
2. user selects a run
3. system displays answer details, evidence references, routing information, and trust metadata
- Postcondition: the user can inspect how the answer was produced

### 3.4.4 Dynamic Models of the System

#### Sequence Diagram Description 1: Upload to Searchable Knowledge

1. user uploads a document from the dataset page
2. frontend sends request to backend
3. backend authenticates workspace and tenant ownership
4. backend stores the file and creates ingestion records
5. worker extracts and normalizes the text
6. worker chunks and indexes the content
7. system marks the document ready for retrieval

#### Sequence Diagram Description 2: Grounded Chat Execution

1. user submits question in chat
2. backend authenticates tenant and resolves conversation context
3. query service analyzes the request
4. retrieval and ranking stages produce candidate evidence
5. generation and verification stages produce grounded answer
6. run trace is persisted
7. response is returned to user with citations and trust fields

#### Activity Diagram Description: Organizational Knowledge Workflow

1. create workspace
2. create dataset
3. upload documents
4. process documents into searchable knowledge
5. create or configure agent
6. attach dataset to agent
7. ask grounded questions through chat
8. inspect runs and outputs

#### State View Description: Document and Run Lifecycle

Document states include upload, processing, indexed, and failed. Query execution states include request received, retrieval, grounding, verification, persisted, and returned. These states help explain both ingestion progress and answer traceability.

## 3.5 Model Validation

### 3.5.1 Problem Validation

The identified problem is validated by the clear mismatch between what organizations need and what basic RAG normally provides. Organizations need reliable, grounded, usable systems. Basic RAG alone often does not satisfy this expectation.

### 3.5.2 Structural Validation

The final system structure reflects the modeled concepts directly: workspaces, datasets, documents, agents, conversations, runs, and tenant-scoped ownership all exist in the implemented design.

### 3.5.3 Behavioral Validation

The modeled workflows for upload, dataset formation, agent attachment, grounded chat, and run inspection align with the product behavior and service interactions of the implemented system.

## 3.6 Chapter Summary

This chapter analyzed the actual problem addressed by the study. It showed that the challenge is not only that traditional document access is inefficient, but also that basic RAG remains too weak for dependable organizational use because of pipeline complexity, unreliable retrieval, and query ambiguity. It also showed that organizations need a practical product, not only a retrieval method. The chapter then translated these realities into concrete requirements and models for the final grounded AI platform. The next chapter presents the design of the advanced pipeline and the product architecture built around it.
