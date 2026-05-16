# Chapter Six: System Evaluation

## 6.1 Preparing Sample Test Plans

The evaluation of Grounded AI had to reflect the same two-part structure used throughout the project.

1. evaluate whether the system improves on basic RAG in meaningful ways
2. evaluate whether the final product works practically for organizations and users

For this reason, evaluation was not limited to surface-level interface testing. It included both technical and product-oriented verification.

### 6.1.1 Evaluation Objectives

The evaluation aimed to verify the following:

1. the system successfully supports organizational document upload and dataset formation
2. the system supports agent creation, dataset attachment, and chat-based grounded interaction
3. the pipeline improves retrieval and grounding behavior beyond a simple basic RAG path
4. the system reduces the effects of query ambiguity through stronger query handling
5. the system improves retrieval reliability through stronger evidence selection behavior
6. the system exposes citations, trust metadata, and inspectable run traces
7. the product workflows are usable for organizational knowledge interaction

### 6.1.2 Types of Tests Used

The evaluation plan included the following categories.

#### Functional Testing

This verifies whether visible product features behave as expected.

#### Integration Testing

This verifies whether multiple subsystems work together across full workflows.

#### Grounding and Retrieval Evaluation

This verifies whether the system behaves more reliably than a basic direct-retrieve-and-generate flow.

#### Product Workflow Evaluation

This verifies whether the platform supports the user and organizational story intended by the project.

#### Traceability and Trust Evaluation

This verifies whether the system exposes the evidence and run details required for user trust.

### 6.1.3 Test Preparation Strategy

Test scenarios were prepared by mapping both the technical pipeline and the product workflows into verifiable cases. This included:

- authentication and access
- workspace creation
- dataset creation
- upload and ingestion progression
- agent creation and dataset attachment
- chat interaction
- grounded answer generation
- run inspection
- API key lifecycle

### 6.1.4 Success Criteria

The project was considered successful if:

- users could upload and organize knowledge successfully
- grounded chat worked over dataset-backed knowledge
- the system produced answers with citations and trust-related structure
- the product exposed inspectable runs and practical management workflows
- the improved pipeline behavior clearly addressed the weaknesses of basic RAG in the target scope

## 6.2 Evaluating the Proposed Design and Solutions

### 6.2.1 Functional Test Cases

Table 6.1 presents representative product-oriented functional test cases.

### Table 6.1. Functional Test Cases

| Test ID | Test Case | Expected Result | Status |
|---|---|---|---|
| TC-01 | User sign-up and sign-in | authenticated session established | Pass |
| TC-02 | Workspace creation | workspace stored and retrievable | Pass |
| TC-03 | Dataset creation | dataset created successfully | Pass |
| TC-04 | Document upload | file stored and ingestion started | Pass |
| TC-05 | Ingestion status visibility | progress visible to user | Pass |
| TC-06 | Agent creation | reusable grounded agent created | Pass |
| TC-07 | Dataset attachment to agent | agent linked to selected dataset | Pass |
| TC-08 | Chat interaction | answer returned through grounded chat flow | Pass |
| TC-09 | Run inspection | run details visible with evidence-related fields | Pass |
| TC-10 | API key creation and revocation | key lifecycle handled correctly | Pass |

### 6.2.2 Pipeline-Oriented Evaluation

The technical side of the evaluation focused on whether the system improves on basic RAG behavior in the target scope of the project.

#### Query Ambiguity Handling Evaluation

Basic RAG often struggles when the user asks broad or imprecise questions. The evaluated system introduces stronger query handling before retrieval. Observed behavior showed that the system was better able to align retrieval with user intent than a naive direct query path.

#### Retrieval Reliability Evaluation

The evaluated system combines multiple retrieval ideas rather than depending on one simple retrieval step. In practice, this improved the quality of evidence selection and reduced the weakness of relying only on a simple dense top-k path.

#### Groundedness and Trust Evaluation

The system exposed citations and answer-related trust structure more clearly than a minimal RAG flow. This improved inspectability and made outputs more practical for organizational use.

### 6.2.3 Integration Evaluation

The final design was also evaluated through end-to-end integration scenarios.

#### Integration Scenario 1: Upload to Searchable Knowledge

Expected flow:

1. create or select dataset
2. upload documents
3. process them through ingestion
4. convert them into searchable grounded knowledge

Observed result:

- the workflow completed successfully and reflected correct dataset and document lifecycle behavior

#### Integration Scenario 2: Dataset to Agent to Chat

Expected flow:

1. create dataset
2. upload knowledge
3. create agent
4. attach dataset to agent
5. ask question through chat
6. receive grounded answer

Observed result:

- the workflow completed successfully and reflected the intended product story of the system

#### Integration Scenario 3: Chat to Run Inspection

Expected flow:

1. user asks question in chat
2. system performs grounded query execution
3. answer is returned
4. run is persisted
5. user opens runs page and inspects output

Observed result:

- the workflow completed successfully and provided inspectable trace behavior

### 6.2.4 Trust and Traceability Evaluation

The final system was evaluated for whether it provides user-visible evidence and trace details rather than acting as a black box.

Observed strengths included:

- answer structure included grounded references
- run information remained inspectable after execution
- the product exposed a stronger trust posture than ordinary basic RAG chat behavior

### 6.2.5 Evaluation of the Product Contribution

From the product perspective, the evaluation showed that the system successfully supports the main organizational workflow intended by the project.

Organizations and users can:

- upload their own documents
- organize them into datasets
- create agents connected to those datasets
- ask questions through chat
- inspect runs and outputs
- manage access through product workflows

This confirms that the project is not only a research pipeline but also a usable platform.

## 6.3 Result Analysis

The evaluation results support the overall claim of the project.

### 6.3.1 Research-Side Analysis

The system demonstrates a stronger approach than ordinary basic RAG because it does not rely only on a minimal direct retrieve-and-generate flow. Instead, it introduces stronger handling around retrieval quality, ambiguity reduction, evidence selection, and trust shaping.

### 6.3.2 Product-Side Analysis

The system also succeeds as a product because it exposes the improved pipeline through practical features that organizations can actually use. The user does not need to manage embeddings, vector indexing, or retrieval orchestration directly. Instead, the user interacts with a product built around datasets, agents, chat, and dashboards.

### 6.3.3 Overall Analysis

The most important result is that the project successfully combines research-driven pipeline improvement with product-oriented system delivery. This balance is one of the main strengths of the final work.

## 6.4 Chapter Summary

This chapter evaluated Grounded AI from both a technical and practical perspective. It showed that the system supports the intended organizational workflows and that the final platform expresses a stronger grounded behavior than a simple basic RAG arrangement. The evaluation therefore supports the study’s overall claim: the project improves on basic RAG and turns that improvement into a real grounded AI product for organizations and users.
