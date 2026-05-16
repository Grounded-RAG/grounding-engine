# Chapter Six: System Evaluation

## 6.1 Overview

This chapter evaluates Grounded AI as both an implemented product and a grounded AI system. The evaluation therefore does not focus only on internal retrieval behavior. It also examines whether the product workflows that matter to organizations work correctly in practice.

The main evaluation question is whether a user can upload organizational data, organize it into datasets, connect those datasets to agents, use chat meaningfully, and inspect results with enough trust and clarity.

## 6.2 Evaluation Objectives

The evaluation aimed to verify that:

1. the platform supports the complete organizational workflow from upload to grounded answer
2. datasets and documents are processed into queryable knowledge successfully
3. agents can be created and attached to datasets correctly
4. chat responses are grounded and traceable
5. run inspection gives useful operational visibility
6. API key workflows support secure access
7. the internal grounding process improves answer quality and reduces unsupported behavior

## 6.3 Types of Evaluation Used

The study used the following evaluation categories.

### 6.3.1 Functional Evaluation

This checks whether visible features and workflows behave as expected.

### 6.3.2 Integration Evaluation

This checks whether multiple subsystems work together across end-to-end product usage.

### 6.3.3 Grounding-Oriented Evaluation

This checks whether answers remain tied to evidence and whether traces are preserved.

### 6.3.4 Product Usability Evaluation

This checks whether the implemented system actually supports the intended organizational workflow clearly.

## 6.4 Functional Test Cases

### Table 6.1. Product Workflow Test Cases

| Test ID | Test Case | Expected Result | Outcome |
|---|---|---|---|
| TC-01 | user sign-up and sign-in | user receives authenticated access | Pass |
| TC-02 | workspace creation | workspace is created and retrievable | Pass |
| TC-03 | dataset creation | dataset is stored successfully | Pass |
| TC-04 | document upload | document and ingestion job are created | Pass |
| TC-05 | ingestion monitoring | job status becomes visible to user | Pass |
| TC-06 | agent creation | reusable agent is stored | Pass |
| TC-07 | dataset attachment to agent | agent gains dataset linkage | Pass |
| TC-08 | chat question over agent | grounded answer is returned | Pass |
| TC-09 | conversation persistence | messages remain linked to conversation | Pass |
| TC-10 | run inspection | prior run details are viewable | Pass |
| TC-11 | dashboard summaries | operational data is visible | Pass |
| TC-12 | API key lifecycle | key creation and revocation work correctly | Pass |

## 6.5 Integration Evaluation

### 6.5.1 Scenario 1: Upload to Dataset Readiness

This scenario verifies that an organizational user can upload files and later use them as knowledge.

Expected flow:

1. create dataset
2. upload file
3. store file and create ingestion job
4. process extraction and indexing
5. mark document as ready

Observed outcome:

The workflow completed correctly and exposed operational state through the product interface.

### 6.5.2 Scenario 2: Dataset to Agent to Chat

This scenario verifies the most important product flow.

Expected flow:

1. create dataset
2. upload documents
3. create agent
4. attach dataset to agent
5. open chat
6. ask question
7. receive grounded answer

Observed outcome:

The workflow executed correctly and demonstrated the central organizational use case of the platform.

### 6.5.3 Scenario 3: Chat to Run Inspection

Expected flow:

1. user asks question in chat
2. answer is generated and returned
3. run trace is stored
4. user inspects run later

Observed outcome:

The workflow succeeded and showed that the system does not hide its execution history.

### 6.5.4 Scenario 4: Developer Access Through API Keys

Expected flow:

1. user creates API key
2. client uses key for access
3. revocation prevents further use

Observed outcome:

The workflow succeeded and confirmed that product access is not limited to the browser interface.

## 6.6 Grounding and Trust Evaluation

The system was also evaluated from the internal grounded-answer perspective.

### 6.6.1 Citation Presence

Grounded responses returned citations when evidence was available. This indicates that the answer flow remained connected to retrieved support.

### 6.6.2 Evidence Alignment

The response structure preserved links between answer content and supporting evidence. This improves user trust compared with systems that answer without visible grounding.

### 6.6.3 Behavior Under Weak Support

When evidence was weak or incomplete, the system surfaced degraded reasoning instead of pretending to have strong support. This is important because it shows the product behaves more honestly in uncertain cases.

### 6.6.4 Run Trace Visibility

The system persisted run information that could later be reviewed through the runs page and dashboard views. This supports inspection, debugging, and organizational accountability.

## 6.7 Evaluation Discussion

The evaluation shows that Grounded AI succeeds in balancing product utility and grounding quality.

From the product side, the system supports the intended organizational workflow clearly: upload data, form datasets, attach them to agents, ask questions in chat, and inspect results.

From the grounding side, the system provides evidence-aware responses, citations, and execution traces that make the product more trustworthy than a simple chat assistant.

The system therefore meets its intended role as a practical document AI platform rather than only a research demonstration.

## 6.8 Chapter Summary

This chapter evaluated Grounded AI as both a product and a grounded AI system. The results show that the implemented platform successfully supports organizational usage through datasets, agents, chat, runs, and API keys while also preserving grounded answering behavior and answer traceability.
