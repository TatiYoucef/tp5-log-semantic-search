# Semantic and Analytical Search on Large-Scale Logs

A Big Data project focused on semantic search, vector embeddings, and large-scale log analysis using modern open-source technologies.

The objective of this repository is to build a complete pipeline capable of processing massive system logs, transforming them into vector embeddings, storing them in a vector database, and performing semantic and analytical queries on top of them.

The project is based on the OpenSSH dataset from Loghub-2.0, containing approximately 638,000 log entries. ([GitHub][1])

---

## Project Goals

This project aims to:

* Process large-scale log datasets using Apache Spark
* Normalize and structure raw logs
* Generate semantic embeddings from log messages
* Store embeddings inside PostgreSQL with pgvector
* Perform semantic similarity search on logs
* Detect recurring errors and similar patterns
* Compare semantic search with traditional keyword-based search
* Analyze temporal evolution of similar log events

---

## Dataset

Current dataset:

* OpenSSH logs from Loghub-2.0
* ~638,946 raw log lines
* Structured CSV and templates included

Dataset source:

* [Loghub-2.0 Repository](https://github.com/logpai/loghub-2.0?utm_source=chatgpt.com)

Research references:

* A Large-Scale Evaluation for Log Parsing Techniques: How Far Are We?
* Loghub: A Large Collection of System Log Datasets for AI-driven Log Analytics

---

## Planned Architecture

```text
Raw Logs
   ↓
Apache Spark Preprocessing
   ↓
Cleaning & Normalization
   ↓
Batch Embedding Generation
   ↓
PostgreSQL + pgvector
   ↓
Semantic Search & Analytics
```

---

## Technologies

The following technologies will be used throughout the project:

* Python
* Apache Spark
* PostgreSQL
* pgvector
* Sentence-Transformers
* Docker & Docker Compose

---

## Repository Structure

```text
.
├── data
│   ├── processed
│   └── raw
│       └── OpenSSH
│
├── notebooks
├── reports
├── sql
│   └── schema.sql
│
├── src   
│
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Planned Features

### Phase 1 — Big Data Pipeline Design

* Dataset exploration
* Log format analysis
* Storage schema design
* Pipeline architecture definition

### Phase 2 — Large-Scale Ingestion & Processing

* Distributed log ingestion with Spark
* Cleaning and normalization
* Data partitioning strategies
* Batch processing pipeline

### Phase 3 — Embeddings & Vector Indexing

* Semantic embedding generation
* Batch vector insertion
* Similarity indexing with pgvector
* Embedding evaluation

### Phase 4 — Semantic Search & Analytics

* Semantic log retrieval
* Similar log detection
* Frequent error grouping
* Temporal error evolution analysis
* Comparison against keyword-based search

---

## Planned Use Cases

The final system should support queries such as:

* Retrieve logs similar to a critical error
* Detect recurring system failures
* Group semantically related log messages
* Analyze the evolution of similar errors over time
* Search logs using natural language

---

## Notes

The project is designed for educational and research purposes in the context of Big Data systems, semantic search, and AI-driven log analytics.

The implementation will prioritize scalability, modularity, and reproducibility.

[1]: https://github.com/logpai/loghub-2.0?utm_source=chatgpt.com "GitHub - logpai/loghub-2.0: A Large-scale Evaluation for Log Parsing Techniques: How Far are We? [ISSTA'24] · GitHub"
