# Chapter Three: Problem Analysis and Modeling

## 3.1 Overview

This chapter analyzes the problem that Grounded AI addresses and translates it into a structured system model. The analysis is intentionally balanced between two viewpoints.

The first viewpoint is the product problem: organizations need a usable system for uploading internal data, organizing it into datasets, assigning it to assistants, chatting over that knowledge, and inspecting previous answers.

The second viewpoint is the grounding problem: inside that product, the system must still solve ambiguity, retrieval reliability, and trust in the answer-generation process.

## 3.2 Existing System and Its Problems

### 3.2.1 Existing System Landscape

Before a platform like Grounded AI, organizations usually rely on one or more of the following:

1. manual browsing through folders and repositories
2. keyword search across file systems or portals
3. static document repositories with no conversational access
4. general AI chat systems that are not grounded in internal knowledge
5. simple RAG demos that retrieve and answer but lack product structure

These approaches may solve part of the problem, but they do not provide a full organizational knowledge product.

### 3.2.2 Product-Level Problems

At the product level, organizations face several difficulties.

#### Lack of Simple Data Onboarding

Many systems do not provide a clean workflow for users to upload files and turn them into a searchable knowledge base.

#### Lack of Knowledge Organization

Even when files can be uploaded, they are often not grouped into manageable datasets. This makes it difficult to control retrieval scope and build focused assistants.

#### Lack of Reusable Assistants

Many systems provide one shared prompt interface instead of reusable agents that can be configured and connected to specific datasets.

#### Lack of Operational Visibility

Users often cannot see ingestion progress, recent runs, answer traces, or whether a document is ready for querying.

#### Lack of Practical Access Control

Organizations need tenant-safe boundaries and API keys for programmatic usage, but research demos rarely prioritize these product features.

### 3.2.3 Research-Level Problems

At the grounding-engine level, the project addresses three central issues.

#### Pipeline Complexity

RAG systems are often difficult to assemble and manage because they require multiple interacting stages such as chunking, embeddings, indexing, retrieval, ranking, prompting, and output shaping.

#### Unreliable Retrieval

Retrieval may select stale, weak, or only partially relevant evidence, causing answers to be less trustworthy.

#### Query Ambiguity

Users frequently ask natural, vague, or broad questions that basic systems do not interpret well.

### 3.2.4 Stakeholders Affected by the Problems

The problem affects the following stakeholders:

1. organizational users who need fast answers from internal documents
2. knowledge operators who upload and maintain datasets
3. team leads and managers who need dependable information
4. agent builders who configure reusable assistants
5. developers who integrate the platform through APIs
6. administrators who need secure tenant-scoped access

### 3.2.5 Impact of the Problems

These problems lead to:

- slower access to internal knowledge
- repeated manual effort
- weak trust in AI-generated answers
- difficulty using AI over company documents at scale
- poor traceability when answers need review
- unnecessary engineering complexity for teams that only want to use their data

## 3.3 Requirements of the Proposed Solution

### 3.3.1 Requirement Elicitation Approach

Requirements were elicited from the project proposal, implementation structure, product workflows, API design, frontend pages, and observed organizational usage needs.

### 3.3.2 Stakeholder Requirements Summary

#### End Users Require

- an easy way to ask questions in natural language
- reliable answers grounded in uploaded data
- clear citations and response confidence
- a chat experience that preserves context

#### Knowledge Operators Require

- dataset creation and organization
- file upload and ingestion tracking
- visibility into document readiness

#### Agent Builders Require

- reusable grounded agents
- dataset attachment and detachment
- conversation flows over selected knowledge collections

#### Developers Require

- stable APIs
- API-key-based access
- inspectable run outputs

#### Administrators Require

- tenant-safe resource separation
- revocable credentials
- controlled access to uploaded organizational data

## 3.4 System Modeling

### 3.4.1 Functional Requirements

The system shall:

1. allow users to sign up and sign in
2. allow users to create and manage workspaces
3. allow users to create and update datasets
4. allow users to upload TXT, PDF, and DOCX documents into datasets
5. create and track ingestion jobs for uploaded documents
6. extract text and prepare retrieval-ready chunks from uploaded files
7. store and search both sparse and dense retrieval representations
8. allow users to create agents and attach datasets to them
9. allow users to create conversations and exchange messages through chat
10. generate grounded answers over attached dataset knowledge
11. return citations and trace metadata with answers
12. preserve run history for later inspection
13. provide dashboard summaries and recent activity
14. allow API key creation and revocation
15. support tenant-scoped access to all major resources

### 3.4.2 Non-Functional Requirements

The system shall provide:

1. usability through a clear product interface
2. reliability through grounded retrieval and answer shaping
3. security through tenant-aware access control
4. traceability through persistent runs and citations
5. maintainability through modular services and schemas
6. portability through containerized infrastructure

### 3.4.3 Actors of the System

The main actors are:

1. visitor
2. authenticated user
3. workspace operator
4. agent builder
5. developer or API client
6. administrator
7. background ingestion worker

### 3.4.4 Major Use Cases

The major use cases are:

1. register and sign in
2. create workspace
3. create dataset
4. upload documents to dataset
5. monitor ingestion status
6. create agent
7. attach dataset to agent
8. open agent chat and ask questions
9. inspect previous runs
10. create and revoke API keys

### 3.4.5 Use Case Descriptions

#### Use Case 1: Create Dataset and Upload Documents

- Primary actor: workspace operator
- Precondition: authenticated user with active workspace
- Main flow:
1. user opens the datasets page
2. user creates a dataset
3. user opens dataset detail page
4. user uploads documents
5. system stores the files and creates ingestion jobs
6. user monitors document and job status until indexing is complete
- Postcondition: dataset becomes ready for grounded retrieval

#### Use Case 2: Create Agent and Attach Dataset

- Primary actor: agent builder
- Precondition: at least one dataset exists
- Main flow:
1. user opens the agents page
2. user creates a new agent
3. user attaches one or more datasets to the agent
4. system stores the agent configuration and attachment links
- Postcondition: reusable grounded agent becomes available for chat

#### Use Case 3: Ask Question Through Chat

- Primary actor: authenticated user
- Precondition: agent exists with attached dataset
- Main flow:
1. user opens agent chat page
2. user selects or creates a conversation
3. user enters a question
4. system retrieves supporting evidence from attached datasets
5. system generates a grounded answer with citations
6. system stores both the assistant message and the run trace
- Postcondition: user receives grounded answer and can inspect the run later

#### Use Case 4: Inspect Run Details

- Primary actor: authenticated user
- Precondition: at least one run exists
- Main flow:
1. user opens runs page or dashboard recent runs
2. user selects a run
3. system displays answer, citations, routing details, and trace metadata
- Postcondition: user can review how the answer was produced

## 3.5 Dynamic Models

### 3.5.1 Sequence Description: Dataset to Chat Flow

1. user creates dataset
2. user uploads file
3. backend stores file and creates ingestion job
4. worker extracts text and writes retrieval artifacts
5. user creates agent and attaches dataset
6. user opens chat and submits question
7. retrieval and grounded answer pipeline execute
8. response and run trace are stored and returned

### 3.5.2 State Description: Document Lifecycle

The document lifecycle includes:

- uploaded
- processing
- indexed
- failed

### 3.5.3 Activity Description: Organizational User Workflow

1. sign in
2. create workspace
3. create dataset
4. upload documents
5. wait for ingestion completion
6. create or select agent
7. ask question in chat
8. inspect run if needed
9. continue conversation or refine data

## 3.6 Model Validation

The model was validated in three ways.

1. structural validation: the modeled entities are represented in the implemented schemas and database
2. workflow validation: the modeled user flows correspond to actual frontend pages and backend APIs
3. grounding validation: the answer flow corresponds to implemented retrieval, response, and trace services

## 3.7 Chapter Summary

This chapter showed that Grounded AI solves both a product problem and a grounding problem. It is designed for organizations that want to upload and use their own knowledge through datasets, agents, and chat, while also improving the quality and trustworthiness of the internal retrieval-and-answer pipeline.
