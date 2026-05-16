# Chapter Five: System Implementation

## 5.1 Overview

This chapter explains how Grounded AI was implemented as a real product platform for organizational document intelligence. The implementation is not limited to a research pipeline. It includes the complete user-facing system through which users sign in, create workspaces, form datasets, upload documents, create agents, use chat, inspect runs, and manage API keys.

At the same time, the implementation also includes the internal grounding logic that makes the product meaningful. That internal logic handles ingestion, retrieval, answer shaping, and trace persistence behind the product workflows.

## 5.2 Implementation Strategy

The implementation followed a product-first but grounding-aware strategy.

1. define the main product objects such as workspace, dataset, document, agent, conversation, and run
2. implement the backend APIs and services around those objects
3. implement ingestion so uploaded files become usable knowledge
4. implement grounded retrieval and response flows
5. implement frontend pages that expose the product clearly to users
6. connect the product layer and grounding layer through traceable workflows

This strategy helped ensure that the system was not only academically interesting but also usable by organizations.

## 5.3 Development Tools and Technologies

### 5.3.1 Programming Languages

The system uses:

- Python for backend services and data-processing logic
- TypeScript for frontend development

### 5.3.2 Backend Technologies

The backend was implemented with:

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic schemas

These tools were selected because they support API-first development, schema validation, modular service organization, and clean data modeling.

### 5.3.3 Frontend Technologies

The frontend was implemented with:

- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS

These tools were selected to support a responsive product interface with page-based workflows and API-driven state updates.

### 5.3.4 Infrastructure Technologies

The infrastructure stack includes:

- PostgreSQL
- Qdrant
- MinIO
- Redis
- Docker Compose

This stack allows the system to manage structured data, vector search, file storage, support services, and reproducible local deployment.

## 5.4 Backend Implementation

### 5.4.1 Application Entry and Route Structure

The backend application is initialized through the FastAPI entry point and versioned route composition. The API layer exposes endpoints for:

- authentication
- workspaces
- datasets
- documents
- agents
- conversations
- direct query
- runs
- dashboard
- API keys

This route structure reflects the product model directly.

### 5.4.2 Authentication and Tenant Context

Authentication is implemented through API keys and email-based preview access. The authentication layer resolves tenant context and ensures that all downstream operations remain tenant-scoped. This is essential for an organizational platform where one tenant's data must not mix with another's.

### 5.4.3 Data Model Implementation

The core implemented models include:

- Tenant
- APIKey
- Workspace
- Dataset or namespace entity
- Document
- DocumentChunkRecord
- IngestionJob
- Agent
- AgentDataset
- Conversation
- Message
- QueryTrace

These models are important because they represent both the product structure seen by users and the internal structure used by the grounding engine.

## 5.5 Product Workflow Implementation

### 5.5.1 Workspace and Dataset Formation

The system allows users to create workspaces and then create datasets inside those workspaces. Dataset formation is one of the most important product features because it gives organizations a practical way to organize knowledge into manageable retrieval scopes.

In implementation terms, datasets are not just file folders. They are the boundary used for document ownership, retrieval scope, and later agent attachment.

### 5.5.2 Document Upload and Ingestion

Document upload is implemented as a structured workflow rather than a simple file post.

The process includes:

1. validating the file
2. computing checksum information
3. checking duplicates
4. storing the source file in object storage
5. creating document and ingestion-job records
6. handing heavy processing to background ingestion

This design keeps the product responsive while still preparing data correctly for grounded retrieval.

### 5.5.3 Ingestion Processing

The ingestion worker transforms uploaded files into retrieval-ready artifacts. It performs text extraction, normalization, chunk creation, sparse indexing, and dense indexing. This is the point where organizational uploads become usable AI knowledge.

### 5.5.4 Agent Implementation

Agents are implemented as reusable grounded assistants. A user can create an agent, store its instructions, and attach datasets to it. This gives the product an important practical dimension because the platform is not limited to one general assistant. Different agents can serve different teams, domains, or workflows.

### 5.5.5 Conversation and Chat Implementation

The chat experience is implemented through conversations and messages linked to an agent. When a user opens the chat page, asks a question, and receives an answer, that answer is connected to both the conversation history and the grounding run.

This means the chat page is not only a UI surface. It is a persistent product workflow backed by dataset-attached knowledge and traceable execution.

### 5.5.6 Dashboard and Runs Implementation

The dashboard and runs pages expose operational visibility. Dashboard services aggregate recent jobs and recent runs. The runs subsystem stores answer traces and allows them to be inspected later. This is one of the features that makes the product suitable for organizations that care about transparency.

### 5.5.7 API Key Management Implementation

API keys are implemented to support secure programmatic access. The system supports key creation, listing, last-used visibility, and revocation. This allows the product to be used not only through the browser but also through developer workflows.

## 5.6 Grounding Engine Implementation

The internal grounding engine is the research-oriented part that operates behind the product experience.

### 5.6.1 Chunk Preparation

The system prepares extracted text into retrieval-ready chunks. This ensures that uploaded documents can be searched and cited at useful granularity.

### 5.6.2 Sparse and Dense Retrieval

The retrieval system uses PostgreSQL full-text search for sparse retrieval and Qdrant for dense semantic retrieval. This combination improves coverage across both exact and meaning-based questions.

### 5.6.3 Fusion and Evidence Selection

After retrieval, the system combines results and selects the most useful evidence. This reduces the chance that weak first-pass retrieval alone determines the final answer.

### 5.6.4 Answer Construction and Response Shaping

The answer layer builds grounded responses from the selected evidence. The response is shaped into a structured form with citations and supporting metadata rather than being returned as an unstructured model completion.

### 5.6.5 Verification and Trace Persistence

The verification and trace components preserve execution details so that the system can later expose what happened during a grounded answer. This contributes directly to trust and inspectability.

## 5.7 Frontend Implementation

The frontend translates backend functionality into usable pages.

### 5.7.1 Implemented Pages

The major pages include:

- home page
- login page
- sign-up page
- onboarding page
- dashboard page
- datasets page
- dataset detail page
- agents page
- agent chat page
- runs page
- settings page

### 5.7.2 Product Experience Design in the Frontend

The frontend was implemented to make the system understandable to non-expert users. The dataset pages focus on knowledge organization and upload state. The agents page focuses on reusable assistants. The chat page focuses on asking questions naturally. The runs page focuses on visibility. The settings page focuses on access management.

This reflects the product goal of making grounded AI practical rather than complicated.

## 5.8 Challenges Encountered During Development

Several challenges were encountered.

### 5.8.1 Balancing Product Simplicity and Grounding Strength

The system had to remain simple for users while still using a meaningful internal grounding process.

### 5.8.2 Maintaining Tenant-Safe Boundaries

Because the platform is organization-oriented, ownership and scoping had to be enforced carefully across datasets, agents, conversations, and runs.

### 5.8.3 Turning Uploads into Searchable Knowledge Reliably

File storage, extraction, ingestion states, and indexing had to work together so users could trust that uploaded data would become usable.

### 5.8.4 Making Chat Trustworthy Rather Than Merely Fluent

The system needed to ensure that the chat product experience remained tied to evidence, not just good wording.

## 5.9 Chapter Summary

This chapter showed how Grounded AI was implemented as a complete product platform backed by a grounding engine. It described the implementation of authentication, workspaces, datasets, document upload, ingestion, agents, chat, runs, dashboard features, and API keys, while also explaining the internal retrieval and response layers that make the product grounded and useful.
