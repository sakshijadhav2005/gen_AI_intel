# Software Requirements Specification (SRS) for VeriCheck

## 1. Introduction
### 1.1 Purpose
This document provides the Software Requirements Specification (SRS) for VeriCheck, an automated fact-checker designed to detect misinformation in vernacular Indian languages at scale.

### 1.2 Scope
VeriCheck aims to process at least 5,000 posts per minute, identifying factual claims from text and verifying them against a verified facts database. It targets eight Indian languages: Hindi, Marathi, Tamil, Bengali, Telugu, Kannada, Gujarati, and Punjabi. The system uses a tiered architecture to handle volume efficiently, minimizing expensive LLM API calls to only 5-10% of posts.

## 2. System Architecture & Design
VeriCheck employs a five-tier processing pipeline to achieve high throughput and context accuracy while minimizing costs.

*   **Tier 0 - Ingestion:**
    *   **Components:** Kafka (production) / Redis Streams (development), Web scrapers (Playwright MCP, fetch MCP).
    *   **Function:** Accepts 100% of posts from social media and news sites, publishing them to a durable message queue (`raw-posts`).
*   **Tier 1 - Pre-filter:**
    *   **Components:** `fastText` (language detection), `spaCy` NER + custom rules (claim extraction), `datasketch` MinHash (duplicate detection).
    *   **Function:** Filters out unsupported languages, opinions, jokes, and questions, reducing volume by ~60%. Prevents reprocessing of near-duplicate posts.
*   **Tier 2 - Hybrid Retrieval and Ranking:**
    *   **Components:** BM25 (`rank_bm25`), FAISS (`faiss-cpu`), `sentence-transformers` embeddings, MiniLM cross-encoder reranker.
    *   **Function:** Processes the remaining ~40% of posts. Performs simultaneous keyword and semantic searches against the verified facts database. Results are merged and reranked for accuracy. A confidence gate determines if the top match is sufficient or if Tier 3 is needed.
*   **Tier 3 - LLM Reasoning:**
    *   **Components:** Claude or GPT-4o API.
    *   **Function:** Handles 5-10% of ambiguous claims that cannot be confidently resolved by Tier 2. Performs deep reasoning against retrieved context.
*   **Tier Output - Delivery:**
    *   **Components:** FastAPI endpoint, Dashboard, Webhooks.
    *   **Function:** Delivers final verdicts (TRUE, FALSE, MISLEADING, UNVERIFIABLE) along with confidence scores and evidence chains.

## 3. Technology Stack
*   **Message Queue:** Apache Kafka / Redis Streams
*   **Language Detection:** fastText (Meta)
*   **Claim Extraction:** spaCy (with Indian language models)
*   **Duplicate Detection:** datasketch MinHash
*   **Keyword Retrieval:** rank_bm25 (BM25)
*   **Vector Search:** FAISS (Meta)
*   **Embeddings & Reranking:** sentence-transformers (multilingual embeddings, MiniLM cross-encoder)
*   **Database:** PostgreSQL + pgvector
*   **Cache:** Redis
*   **LLM API:** Claude or GPT-4o
*   **API Framework:** FastAPI (Python)
*   **Scraping:** Playwright MCP, fetch MCP, DuckDuckGo MCP
*   **Monitoring/Orchestration:** Prometheus, Grafana, Docker, Kubernetes

## 4. Requirements
### 4.1 Functional Requirements
1.  **Ingestion:** The system must accept posts from various sources and queue them durably.
2.  **Language Filtering:** The system must detect the language of a post and process only supported Indian languages.
3.  **Claim Extraction:** The system must identify and extract factual claims from text, ignoring opinions and non-factual content.
4.  **Deduplication:** The system must identify and drop near-duplicate claims to avoid redundant processing.
5.  **Fact Retrieval:** The system must retrieve relevant verified facts using both keyword and semantic search.
6.  **Reranking:** The system must rerank retrieved facts based on relevance and authority.
7.  **LLM Verification:** The system must route ambiguous claims to an LLM for reasoning.
8.  **Verdict Generation:** The system must produce a structured verdict (JSON) containing a label, confidence score, and evidence.
9.  **API:** The system must provide a REST API (via FastAPI) to submit claims and retrieve verdicts.

### 4.2 Non-Functional Requirements
1.  **Throughput:** The system must process at least 5,000 posts per minute.
2.  **Latency:** Tier 1 operations must complete in < 5ms. Tier 2 operations must complete in < 200ms. End-to-end processing (excluding Tier 3) should be fast.
3.  **Cost:** LLM API usage must be restricted to 5-10% of total volume. All other core components must be open-source/free.
4.  **Accuracy:** Retrieval must prioritize accurate, up-to-date facts to avoid confusion.

## 5. Data Flow (Verdict JSON Structure)
The system outputs a standardized JSON verdict:

```json
{
  "verdict_id": "uuid",
  "item_id": "uuid",
  "label": "FALSE",
  "confidence": 0.94,
  "evidence": [
    {
      "fact_id": "uuid",
      "text": "...",
      "source": "who.int",
      "date": "2024-01-15"
    }
  ],
  "explanation": "The claim contradicts WHO guidance published January 2024.",
  "tier_reached": 2,
  "model_version": "v1.2",
  "human_reviewed": false
}
```

Labels can be: `TRUE`, `FALSE`, `MISLEADING`, or `UNVERIFIABLE`.
