# Chapter Five: System Implementation

## 5.1 Reviewing the Design Solution

The implementation stage began after the system design had clearly established the two main contributions of the project.

The first contribution is the research contribution: improving on basic RAG by addressing pipeline complexity, unreliable retrieval, and query ambiguity.

The second contribution is the product contribution: building a real grounded AI platform for organizations and users so that they can use the improved pipeline without building RAG themselves.

Before implementation, the design was reviewed against the following questions:

1. does the system really improve on basic RAG rather than merely reproduce it?
2. does the system turn the improved pipeline into a usable product?
3. can organizations upload and organize their knowledge without managing the internal complexity themselves?
4. can users interact through datasets, agents, and chat rather than only low-level technical endpoints?
5. does the final implementation preserve groundedness, citations, trust signals, and traceability?

The answer to these questions guided the implementation strategy. As a result, development proceeded with two parallel implementation goals:

1. implement the advanced grounding pipeline correctly
2. implement the user-facing and organization-facing product workflows around it

## 5.2 Deciding on the Development Tools

The implementation required tools suited for both AI-oriented backend workflows and a practical product interface.

### 5.2.1 Programming Languages

The system uses:

- Python for backend services, ingestion, retrieval, and grounding logic
- TypeScript for frontend development and typed client-side workflows

Python was selected for its strong ecosystem in API development, document processing, and AI integration. TypeScript was selected to improve maintainability and correctness in frontend product development.

### 5.2.2 Backend Framework and Tools

The backend uses:

- FastAPI
- SQLAlchemy Async ORM
- Alembic
- provider adapters and retrieval-related services

FastAPI was chosen because it supports modern asynchronous API development, structured schemas, and service-oriented design.

### 5.2.3 Frontend Framework and Tools

The frontend uses:

- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS
- Framer Motion

These tools support the development of a complete product experience including datasets, agents, chat, dashboard, and settings workflows.

### 5.2.4 Storage and Retrieval Tools

The system uses:

- PostgreSQL for operational persistence and sparse retrieval support
- Qdrant for dense vector retrieval
- MinIO for document and artifact storage
- Redis as a support component

This infrastructure was selected because it separates product state, file storage, and vector retrieval concerns in a practical way.

### 5.2.5 Development Environment and Infrastructure Tools

The development environment uses:

- Visual Studio Code
- Git and GitHub
- Docker and Docker Compose
- Pytest and frontend testing tools
- OpenAPI and route verification tooling

These tools made the system repeatable, testable, and practical to develop as both an AI pipeline and a product platform.

## 5.3 Developing the Solution

The implementation of Grounded AI can be understood through the same two-part story used throughout the document:

1. implementation of the advanced adaptive pipeline
2. implementation of the grounded AI product around that pipeline

### 5.3.1 Backend Application Entry and API Routing

The backend application provides the product and pipeline capabilities through structured routes and service orchestration. The API layer exposes endpoints for authentication, workspaces, datasets, uploads, agents, conversations, grounded query execution, runs, dashboard views, and API keys.

This is important because the platform is not exposed only as an experimental retrieval module. It is exposed as a full product backend.

### 5.3.2 Authentication and Tenant Context Implementation

Authentication and tenant resolution are implemented so that all major actions occur in the correct ownership scope. This supports organizational separation and makes the product safe for multi-tenant use.

The implementation includes:

- API key lookup and validation
- tenant-context construction
- ownership checks on resources such as workspaces, datasets, agents, and runs

### 5.3.3 Workspace and Dataset Implementation

One of the most important product features is that users do not simply upload files into one flat corpus. Instead, they organize knowledge into datasets.

The implementation includes:

- workspace creation and listing
- dataset creation, retrieval, and update
- dataset-level metadata and management
- document listing within dataset context

This is a core part of the product contribution because it gives organizations a practical way to structure their internal knowledge.

### 5.3.4 Document Upload and Ingestion Implementation

The platform supports document upload for supported file types. After upload, the system creates the necessary records and begins ingestion processing.

This implementation includes:

- file validation
- canonical storage handling
- duplicate detection
- document record creation
- ingestion job creation and tracking

This stage is where raw organizational data begins to enter the grounded AI workflow.

### 5.3.5 Extraction and Normalization Implementation

Uploaded documents are converted into normalized textual content that can be processed further. This is necessary because organizations upload knowledge in different file formats but the grounding pipeline needs a consistent representation for chunking and retrieval.

### 5.3.6 Semantic Chunking Implementation

The system implements chunking in a way intended to preserve meaning more effectively than naive fixed-size splitting. This supports the research goal of improving on basic RAG.

By producing more coherent evidence units, the system improves the quality of downstream retrieval and answer grounding.

### 5.3.7 Sparse and Dense Indexing Implementation

The implementation supports both lexical and semantic retrieval paths.

- sparse or lexical indexing supports exact wording and text search behavior
- dense indexing supports semantic retrieval over embeddings

This directly reflects the decision to improve on basic single-path retrieval.

### 5.3.8 Query Analysis and Transformation Implementation

The system analyzes user queries before retrieval. This is important because one of the main research goals is reducing query ambiguity.

The implementation supports:

- identification of the incoming request context
- preparation of retrieval-oriented query behavior
- handling of broad or natural-language user questions in a more deliberate way than direct pass-through retrieval

### 5.3.9 Hybrid Retrieval Implementation

The retrieval implementation combines sparse and dense methods rather than relying on only one of them. This improves evidence selection for both exact phrasing and semantic meaning.

This is one of the clearest ways the system improves on basic RAG in practice.

### 5.3.10 Ranking and Evidence Selection Implementation

After initial retrieval, the system refines candidate evidence before answer generation. This includes stronger ranking and evidence packaging logic so that the grounding stage receives better support material.

This improves reliability compared with simply sending the first top-k retrieved chunks to the model.

### 5.3.11 Grounded Query Orchestration Implementation

The main query service coordinates the grounding workflow. It accepts the query request, resolves the relevant context, performs retrieval, packages evidence, calls generation, applies trust-oriented shaping, and persists the resulting run.

This service is important because it embodies the transition from a set of isolated techniques into one working adaptive grounded flow.

### 5.3.12 Response Shaping and Structured Output Implementation

The system does not return only raw model text. It shapes the response into a structured grounded output that includes citations and trust-related fields. This supports the project goal of making answers inspectable and useful.

### 5.3.13 Verification Implementation

Verification is implemented so that final answers can be assessed against their support. This helps reduce hallucination risk and makes the system more dependable than basic RAG approaches that generate directly from loosely selected context.

### 5.3.14 Agent Implementation

Agents are a key product feature. The platform allows users to create reusable grounded assistants and attach datasets to them.

This means the product is not only a dataset query tool. It also supports assistant-oriented workflows where different teams or use cases can have different grounded agents.

### 5.3.15 Conversation and Chat Implementation

The chat page is one of the primary user-facing features of the system. Conversation support allows users to interact naturally with the platform rather than thinking in terms of retrieval operations.

The implementation includes:

- conversation creation and management
- message persistence
- grounded answer generation in conversational flow
- linking of chat responses to runs and evidence

This is central to the product contribution because it is how many users experience the intelligence core of the system.

### 5.3.16 Run Trace and Inspection Implementation

Every grounded execution is persisted as a run or trace record. This supports inspectability and helps the system avoid becoming a black box.

Stored details include:

- query and routing context
- retrieved evidence references
- selected support references
- citations and trust-related metadata
- answer-related trace information

### 5.3.17 Dashboard and Product Visibility Implementation

The dashboard implementation provides operational visibility into the platform. It aggregates counts, recent activity, ingestion progress, and run summaries so that users and operators can understand system activity.

This matters because a serious organizational product requires not only intelligence, but also visibility and manageability.

### 5.3.18 API Key Management Implementation

API key support allows developer-facing integration while preserving controlled access. This is part of the product story because organizations often need both UI-based workflows and programmatic access.

### 5.3.19 Frontend Product Implementation

The frontend translates the backend and intelligence capabilities into practical workflows. Major implemented areas include:

- landing page
- login and sign-up pages
- onboarding flow
- dashboard
- datasets page
- dataset detail page
- agents page
- agent chat page
- runs page
- settings page

These pages collectively form the real product experience of Grounded AI.

### 5.3.20 Implementation of the Research Contribution and Product Contribution

The final implementation can be summarized in two parts.

#### Research Contribution in Implementation

The system improves on basic RAG by implementing stronger preprocessing, retrieval, ranking, verification, and attribution behavior than a simple vector-only top-k pipeline.

#### Product Contribution in Implementation

The system turns that improved grounding pipeline into a usable platform where organizations can upload data, structure it into datasets, create grounded agents, interact through chat, inspect runs, and manage access.

## 5.4 Challenges Encountered During Development

Several key challenges were addressed during implementation.

### 5.4.1 Balancing Research Depth and Product Usability

One challenge was ensuring that the project did not become only a technical retrieval experiment or only a surface-level product shell. The solution was to build the product directly around the improved pipeline rather than treating the two as separate efforts.

### 5.4.2 Improving RAG Without Overcomplicating the User Experience

Another challenge was that the internal pipeline became more advanced than basic RAG, but the user experience still needed to remain simple. The platform solves this by keeping the complexity inside the system while exposing a user-friendly workflow built around uploads, datasets, agents, and chat.

### 5.4.3 Preserving Organizational Separation

Because the system is intended for organizational use, data ownership and resource boundaries had to be implemented carefully across datasets, agents, and conversations.

### 5.4.4 Making Trust Visible

It was not enough for the system to be grounded internally. The answer quality also had to be visible to the user through citations, structure, and traceability.

## 5.5 Chapter Summary

This chapter explained how the final system was implemented. It showed that the project was built around two connected goals: implementing an advanced adaptive pipeline that improves on basic RAG, and implementing a practical grounded AI product around that pipeline. The result is a system where organizations do not need to build RAG themselves. Instead, they can upload knowledge, organize it into datasets, create agents, use chat, inspect runs, and benefit from a stronger grounded intelligence core behind the scenes.
