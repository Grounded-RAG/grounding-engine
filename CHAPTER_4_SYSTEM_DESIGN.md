# Chapter Four: System Design

## 4.1 Overview

This chapter presents the design of the final system. The design must satisfy the two main commitments of the study.

The first commitment is the research-side commitment: improve on basic RAG by addressing pipeline complexity, unreliable retrieval, and query ambiguity.

The second commitment is the product-side commitment: transform that improved grounding approach into a usable platform for organizations and users.

For this reason, the design of Grounded AI is not described as only a retrieval flow and not only as a dashboard product. It is described as a combination of both:

1. an advanced adaptive grounding pipeline as the intelligence core
2. a real software platform around that core, including datasets, uploads, agents, chat, run inspection, and access workflows

This chapter explains how these parts fit together into one coherent system.

## 4.2 Specifying the Design Goals

The design goals of the system follow directly from the problem analysis and study objectives.

### 4.2.1 Improve Basic RAG

The system should improve on basic RAG rather than simply reproduce it. This means the design must include mechanisms that reduce ambiguity, strengthen retrieval, and improve trust.

### 4.2.2 Reduce Complexity for Organizations

Organizations should not need to design and orchestrate an entire RAG stack by themselves. The platform should absorb the complexity of ingestion, indexing, retrieval, grounding, and inspection into one manageable product.

### 4.2.3 Support Practical Knowledge Workflows

The system should support how organizations actually use knowledge. This includes uploading documents, grouping them into datasets, connecting them to agents, chatting over those datasets, and inspecting outputs.

### 4.2.4 Increase Trust and Groundedness

The system should not only answer questions. It should answer with evidence, structure, traceability, and user-visible trust signals.

### 4.2.5 Preserve Security and Separation

The platform should isolate organizational data correctly through tenant and dataset ownership boundaries.

### 4.2.6 Remain Extensible

The architecture should support future improvements in retrieval, verification, product features, and organizational integration.

## 4.3 System Design

### 4.3.1 Design Overview

Grounded AI is designed as a layered platform whose central intelligence is an advanced adaptive RAG pipeline. Around that pipeline, the product provides the workflows that organizations and users actually interact with.

At a high level, the system can be understood in two connected views.

#### View 1: Intelligence-Core View

This view explains how the system improves on basic RAG internally through stronger preprocessing, retrieval, ranking, grounding, verification, and attribution.

#### View 2: Product-Workflow View

This view explains how the system appears to the user as a product. Users upload documents, organize them into datasets, connect datasets to agents, ask questions through chat, inspect runs, and manage access.

The design is successful only if both views work together.

### 4.3.2 The Advanced Adaptive Pipeline

The intelligence core of the system is an advanced adaptive RAG pipeline designed to improve basic RAG. Rather than treating ordinary retrieval and generation as sufficient, the design introduces a more deliberate sequence of stages.

#### Stage 1: Pre-Retrieval Improvement

This stage improves the quality of what enters retrieval.

##### 1. Query Transformation

The system analyzes the user request and improves it for retrieval when necessary. Broad or vague queries may be decomposed into clearer sub-queries so that retrieval is better aligned with the actual user intent.

##### 2. Semantic Chunking

The system prepares document content in semantically coherent segments rather than relying only on arbitrary fixed-length chunking. This helps preserve meaning and improves the usefulness of retrieved evidence.

##### 3. Namespace Isolation

The system ensures that all retrieval happens within the correct organizational and dataset boundaries. This supports product safety and organizational data separation.

#### Stage 2: Retrieval Improvement

This stage strengthens evidence selection compared with basic vector-only retrieval.

##### 4. Hybrid Retrieval

The system combines lexical retrieval and semantic retrieval. This design improves performance on both exact wording and conceptual similarity.

##### 5. Temporal Ranking

When freshness matters, the system incorporates time-aware ranking so that recent information can be favored over outdated material.

#### Stage 3: Evidence Refinement and Correction

This stage improves the quality of the retrieved evidence before final answer production.

##### 6. Reranking

The system refines the order of retrieved candidates so that the strongest evidence is prioritized for grounding.

##### 7. Corrective Retrieval Behavior

When the first retrieval result is weak, incomplete, or low-confidence, the system can trigger additional corrective behavior instead of proceeding blindly.

##### 8. Internal Retrieval Support

For cases that require broader context, the system can inspect larger bodies of text or deeper internal evidence rather than depending only on narrow chunk retrieval.

#### Stage 4: Grounded Answer and Trust Layer

This stage focuses on answer quality, structure, and user trust.

##### 9. Verification Loop

The system evaluates the grounded answer in relation to its supporting evidence and determines whether the answer is sufficiently supported.

##### 10. Structured Enforcement

The system shapes the response into a structured form so that citations and trust metadata are consistently represented.

##### 11. Source Attribution

The final answer links back to the supporting evidence so that users can inspect where claims came from.

### 4.3.3 Adaptive Behavior and Execution Depth

The system is adaptive because not all queries need the same amount of processing. Some questions are simple and can be answered quickly. Others require deeper retrieval, stronger verification, and broader evidence handling.

For this reason, the design includes routing behavior that can apply different execution depth depending on the nature of the request. This is one of the ways the system improves on basic RAG, which often treats all queries with the same fixed path.

### 4.3.4 Product Architecture Around the Pipeline

The improved pipeline is only one part of the solution. It becomes useful to organizations because it is embedded inside a real platform.

#### Workspace Layer

The workspace layer groups product activity for an organization or user environment. It provides the top-level structure for datasets, agents, conversations, and operational visibility.

#### Dataset Layer

Datasets are the main knowledge-organization unit of the product. Instead of treating all uploaded documents as one undifferentiated corpus, the system allows users to organize knowledge into datasets. This makes knowledge management more practical and allows grounded behavior to be targeted.

Each dataset acts as a curated knowledge collection that can receive uploaded documents, be processed into grounded evidence, and later be attached to agents or queried directly.

#### Document Upload and Ingestion Layer

This part of the design handles the path from raw user documents to searchable grounded knowledge. The product allows users to upload supported files, stores them safely, tracks their ingestion state, and transforms them into indexed evidence used by the grounding pipeline.

#### Agent Layer

Agents are reusable grounded assistants. They allow users to define a named assistant and connect it to one or more datasets. This design is important because organizations often want different assistants for different domains or teams, such as policy support, technical support, research assistance, or internal operations.

#### Conversation and Chat Layer

The chat page is one of the main user interaction points. It gives users a natural-language interface for asking grounded questions. Instead of manually navigating the retrieval system, the user interacts through conversation. The system then applies the intelligence pipeline behind the scenes and returns grounded answers with citations and trust signals.

#### Run Inspection and Traceability Layer

The product includes run visibility so that users can inspect previous executions. This is essential because a grounded system should not act as a black box. Users need to see evidence references, answer structure, and other trace details.

#### Dashboard and Operational Visibility Layer

The dashboard gives product-level visibility into the system. It helps users and operators monitor datasets, documents, ingestion progress, recent runs, and system activity. This makes the platform operationally practical rather than only technically functional.

#### API Access Layer

The platform also supports developer-facing access through API keys and backend endpoints. This allows the system to be integrated into broader workflows while still preserving product structure and access control.

### 4.3.5 Proposed Software Architecture

The system uses a layered software architecture.

#### Presentation Layer

This is the frontend product interface built with React and TypeScript. It provides the landing page, authentication pages, onboarding, dashboard, dataset pages, agent pages, chat workflows, runs page, and settings.

#### API and Application Layer

This layer is implemented with FastAPI. It exposes the product capabilities through structured REST endpoints.

#### Domain Service Layer

This layer contains the main business logic for documents, datasets, agents, conversations, retrieval, generation, verification, and dashboard aggregation.

#### Ingestion and Processing Layer

This layer handles extraction, chunking, indexing, and background processing after upload.

#### Grounding and Retrieval Layer

This layer implements the adaptive RAG logic that improves on basic RAG.

#### Persistence and Infrastructure Layer

This layer includes PostgreSQL, Qdrant, MinIO, Redis support, and Docker-managed infrastructure.

### 4.3.6 Subsystem Decomposition

The final system can be decomposed into the following major subsystems.

1. authentication and tenant-context subsystem
2. workspace-management subsystem
3. dataset-management subsystem
4. document upload and ingestion subsystem
5. chunking and indexing subsystem
6. retrieval subsystem
7. grounding and response-shaping subsystem
8. verification subsystem
9. agent and conversation subsystem
10. dashboard and run-inspection subsystem
11. API key management subsystem

### 4.3.7 Database Design

The database design is centered on organizational ownership and grounded traceability.

#### Key Entities

The major entities include:

- tenant
- API key
- workspace
- dataset
- document
- document chunk record
- ingestion job
- agent
- agent-dataset attachment
- conversation
- message
- query trace or run record

#### Design Rationale

This design reflects the product story directly. Organizations need structured ownership of knowledge, datasets need to own documents, agents need to attach to datasets, conversations need to persist interaction history, and runs need to preserve grounded execution details.

### 4.3.8 Deployment Design

The deployment design separates user interaction, application logic, storage, and retrieval infrastructure.

#### Main Deployment Nodes

1. client browser
2. frontend web application
3. FastAPI backend service
4. PostgreSQL database
5. Qdrant vector service
6. MinIO object storage
7. Redis support service

This structure supports both product usability and pipeline operation.

### 4.3.9 User Interface Design

The user interface is designed to expose the platform as a practical organizational product.

#### Main Pages

- landing page
- login and sign-up pages
- onboarding page
- dashboard page
- datasets page
- dataset detail page
- agents page
- agent chat page
- runs page
- settings page

#### UI Design Intent

Each page supports part of the user story:

- datasets support knowledge formation
- uploads support corpus growth
- agents support reusable grounded assistants
- chat supports natural-language interaction
- runs support traceability
- dashboard supports visibility
- settings support access control

### 4.3.10 Security Design

Security is part of both the research and product story because grounded organizational systems must protect data boundaries.

#### Authentication and Authorization

Requests are authenticated and resolved within the correct ownership scope.

#### Data Isolation

Tenant and dataset ownership are preserved across storage and retrieval behavior.

#### Safe Operational Access

API keys, resource checks, and structured ownership rules help protect the product environment.

## 4.4 Verifying the Requirements in the Design

The design was verified against the requirements identified in Chapter Three.

### 4.4.1 Verification of Research-Side Requirements

- improved query handling is represented through query analysis and transformation behavior
- improved retrieval quality is represented through hybrid retrieval, temporal ranking, and reranking
- corrective behavior is represented through recovery-oriented retrieval handling
- trust improvements are represented through verification, structured enforcement, and attribution

### 4.4.2 Verification of Product-Side Requirements

- dataset formation is represented through dataset and document subsystems
- organizational knowledge upload is represented through ingestion workflows
- grounded agents are represented through agent and attachment structures
- chat interaction is represented through conversation and message workflows
- run visibility is represented through trace persistence and run inspection
- operational usability is represented through dashboard and settings workflows

## 4.5 Chapter Summary

This chapter presented the complete design of Grounded AI. It showed how the system improves on basic RAG through an advanced adaptive pipeline and how that pipeline is embedded inside a real product for organizations and users. The design makes clear that the final system is not only a research idea and not only a software interface. It is a grounded AI platform whose internal intelligence core solves RAG weaknesses and whose product workflows make that intelligence usable in practice.
