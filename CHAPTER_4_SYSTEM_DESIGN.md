# Chapter Four: System Design

## 4.1 Overview

This chapter presents the design of Grounded AI as a complete product platform backed by a grounded retrieval engine. The design is intentionally described from the outside in.

From the outside, users see a product with pages for dashboard, datasets, dataset details, agents, chat, runs, and settings. They upload files, manage datasets, create agents, converse with those agents, and inspect results.

From the inside, the platform uses a retrieval-and-answer architecture that turns uploaded organizational documents into grounded responses. This chapter explains both layers clearly so that the system is understood as a product for organizations, not only as a research pipeline.

## 4.2 Design Goals

The system was designed with the following goals:

1. make grounded AI simple for organizations to use
2. reduce the complexity of building RAG from scratch
3. provide clear product workflows for upload, dataset management, agent usage, and chat
4. improve answer reliability through stronger retrieval and grounded response design
5. preserve traceability through runs, citations, and operational visibility
6. support secure multitenant usage and API-based integration

## 4.3 Overall Product Design

Grounded AI is designed as a multitenant knowledge product with the following major user-facing areas.

### 4.3.1 Authentication and Entry

Users enter the system through sign-up and sign-in flows. Authentication establishes the tenant context that is used to scope workspaces, datasets, agents, conversations, runs, and API keys.

### 4.3.2 Dashboard

The dashboard provides an overview of the workspace state. It aggregates high-level counts and recent operational activity such as recent runs and recent ingestion jobs. This page helps a user understand the health and usage of the system without navigating into every section individually.

### 4.3.3 Datasets Page

The datasets page is where users create and manage knowledge collections. A dataset acts as a logical container for a related set of documents. This design is important because datasets become the retrieval boundary for later grounded answering.

### 4.3.4 Dataset Detail Page

The dataset detail page allows document upload, document listing, and ingestion visibility. This is the page where a user turns files into usable knowledge. Each upload creates document records and ingestion jobs. The design keeps the operational state visible so that users know whether a document is still processing or already indexed.

### 4.3.5 Agents Page

The agents page allows users to create reusable grounded assistants. An agent stores instructions and can be attached to one or more datasets. This is important because the system is not limited to one generic chat experience. Different teams can create different agents for different knowledge domains.

### 4.3.6 Agent Chat Page

The chat page is one of the most important product surfaces. It is where the organizational user interacts with grounded AI directly. The page supports conversational interaction, preserves message history, and returns grounded answers using the datasets attached to the agent. The design treats chat as a serious workflow backed by evidence and traceability rather than a simple prompt box.

### 4.3.7 Runs Page

The runs page exposes previous grounded executions. This gives the system transparency. A user can inspect what happened in prior answers instead of treating the product as an opaque assistant.

### 4.3.8 Settings and API Keys

The settings area includes API key management and capability visibility. This supports organizational and developer use cases in which external clients or services need controlled access to the platform.

## 4.4 Architectural Design

### 4.4.1 Layered Architecture

The system follows a layered architecture with these major layers:

1. presentation layer
2. API and application layer
3. domain service layer
4. ingestion and worker layer
5. retrieval and grounding layer
6. persistence and infrastructure layer

### 4.4.2 Presentation Layer

This layer is implemented in React and TypeScript. It contains the dashboard, dataset, agent, chat, run, and settings interfaces.

### 4.4.3 API and Application Layer

This layer is implemented with FastAPI and exposes endpoints for authentication, workspaces, datasets, documents, agents, conversations, direct query, runs, dashboard data, and API keys.

### 4.4.4 Domain Service Layer

This layer contains the business logic for the product. It coordinates uploads, dataset rules, agent behavior, conversations, run persistence, and grounded response flows.

### 4.4.5 Ingestion and Worker Layer

This layer transforms uploaded files into retrieval-ready artifacts. It handles extraction, chunk formation, indexing, and job-state updates.

### 4.4.6 Retrieval and Grounding Layer

This layer is the core research-engine portion of the system. It handles retrieval, ranking, answer construction, and trust-oriented shaping.

### 4.4.7 Persistence and Infrastructure Layer

This layer uses PostgreSQL for relational and sparse-search data, Qdrant for vector retrieval, MinIO for object storage, Redis for support services, and Docker Compose for local orchestration.

## 4.5 Core Product Entities

The main entities of the platform are:

1. tenant
2. workspace
3. dataset
4. document
5. ingestion job
6. document chunk
7. agent
8. agent-dataset attachment
9. conversation
10. message
11. query trace or run

These entities are important because they define the product model seen by users and the internal model used by the grounding engine.

## 4.6 Subsystem Decomposition

### 4.6.1 Workspace and Dataset Management Subsystem

This subsystem supports the formation and management of knowledge collections. It allows users to create datasets, update them, and inspect related documents and jobs.

### 4.6.2 Document Upload and Ingestion Subsystem

This subsystem receives uploaded files, stores them, creates ingestion jobs, extracts text, and prepares retrieval-ready content.

### 4.6.3 Agent Subsystem

This subsystem allows creation and maintenance of reusable grounded agents. Agents provide the product abstraction through which knowledge is reused.

### 4.6.4 Conversation and Chat Subsystem

This subsystem supports conversational usage over agent-attached knowledge. It stores messages and links responses to grounded runs.

### 4.6.5 Query and Grounding Subsystem

This subsystem accepts a question, retrieves supporting evidence from the selected datasets, shapes the answer, and returns grounded output.

### 4.6.6 Run Trace and Dashboard Subsystem

This subsystem provides transparency into operations and answers by exposing recent runs, recent jobs, summaries, and detailed trace records.

### 4.6.7 API Key and Access Subsystem

This subsystem supports secure client access and credential lifecycle management.

## 4.7 Internal Grounding Design

The internal grounding design explains what happens between user question and final answer.

### 4.7.1 Document Preparation

Uploaded documents are extracted into text and broken into retrieval-ready chunks. This makes organization-owned data queryable.

### 4.7.2 Retrieval Design

The system uses both sparse and dense retrieval so that it can handle exact terminology and semantic meaning together.

### 4.7.3 Fusion and Selection

The retrieval layer combines multiple result sets and selects the most useful evidence candidates for answer generation.

### 4.7.4 Grounded Response Construction

The final answer is constructed from selected evidence and returned with citations and trace data rather than as a free-floating generated paragraph.

### 4.7.5 Trust and Inspection

The design keeps runs available for later inspection so that users can review prior grounded executions.

## 4.8 Database Design

The relational model is tenant-centered. Each major product object belongs to a tenant and is linked through foreign-key relationships. Datasets own documents. Documents produce ingestion jobs and chunks. Agents attach to datasets. Conversations belong to agents. Runs connect answers back to their execution context.

This structure supports both product usability and grounded retrieval boundaries.

## 4.9 Deployment Design

The deployment model includes:

1. browser client
2. frontend web application
3. backend API service
4. PostgreSQL
5. Qdrant
6. MinIO
7. Redis

This separation makes the system easier to reason about and closer to how a real organizational deployment would be structured.

## 4.10 Security Design

Security is built into the design through:

1. authenticated access
2. API key hashing and revocation
3. tenant-scoped resource resolution
4. safe dataset and agent ownership checks
5. trace persistence with controlled metadata

## 4.11 Requirement Verification in the Design

The design satisfies the earlier requirements in the following ways:

1. organizational usability is supported through dashboard, datasets, agents, chat, runs, and settings pages
2. grounded answering is supported through retrieval, evidence selection, and answer shaping services
3. dataset-based knowledge organization is supported through explicit dataset entities and attachment flows
4. reusable assistants are supported through the agent model
5. transparency is supported through run traces and inspection pages
6. secure access is supported through tenant scope and API keys

## 4.12 Chapter Summary

This chapter described Grounded AI as a product-first grounded AI platform. It showed how the design supports organizational use through datasets, agents, chat, dashboard visibility, runs, and settings, while also supporting a stronger retrieval-and-answer engine inside the platform. The chapter makes clear that the implemented system is both a usable product and a grounding architecture.
