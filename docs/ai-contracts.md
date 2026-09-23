# AI Engine & Service Contracts

This document strictly defines the operational and programmatic boundaries between the **Backend**, **AI Engine**, **Database**, and **Background Workers**. By enforcing these programmatic interfaces, we guarantee that the AI layer remains deterministic, auditable, and decoupled from physical data persistence.

## 1. System Boundaries
- **Backend (FastAPI)**: The primary orchestrator. Calls the database, issues tasks to the Background Worker, and exposes HTTP interfaces.
- **AI Engine (Python/LLM)**: A pure, stateless function layer. Accepts text/JSON, returns strongly-typed Pydantic JSON. Cannot query the database independently.
- **Database (PostgreSQL)**: The immutable ledger.
- **Background Worker (Celery/Redis)**: Orchestrates bulk AI processing (e.g., 10,000 row ingestion).

## 2. Standardized AI Result Payload
Every AI interface output must be encapsulated in the following schema:
```json
{
  "data": { ... },
  "metadata": {
    "model_version": "v1.2.0",
    "prompt_version": "v2.1",
    "rules_version": "v1.0",
    "confidence": 0.98,
    "evidence": "Extracted '6IN' from description string.",
    "conflicts": [],
    "processing_time_ms": 145
  }
}
```

---

## 3. Core Interface Definitions

### 3.1 MaterialProcessor
Orchestrates the entire AI ingestion pipeline for a raw source string.
- **Input**: `SourceMaterial` object.
- **Output**: `NormalizedMaterial` object.
- **Errors**: `ProcessingTimeoutError`, `MalformedInputError`
- **Version**: `v1.0`
- **Timeout**: 5000ms
- **Retry Behavior**: Exponential backoff (max 3 retries).
- **Observability Metadata**: `source_id`, `cpse_code`, `pipeline_duration_ms`

### 3.2 Normalizer
Strips punctuation, harmonizes casing, and standardizes descriptions.
- **Input**: Raw description `string`.
- **Output**: Normalized `string`.
- **Errors**: `NormalizationFailure`
- **Version**: `v1.1`
- **Timeout**: 500ms
- **Retry Behavior**: No retries (deterministic operation).
- **Observability Metadata**: `text_length_before`, `text_length_after`

### 3.3 UOMNormalizer
Maps arbitrary Units of Measure (e.g., "pcs", "each") to standard dimensions.
- **Input**: Raw UOM `string`.
- **Output**: Standardized UOM code (`string`).
- **Errors**: `UnrecognizedUOMError`
- **Version**: `v1.0`
- **Timeout**: 100ms
- **Retry Behavior**: None.
- **Observability Metadata**: `mapped_dimension`

### 3.4 AttributeExtractor
Uses LLM/Regex to extract key-value pairs (size, voltage, material) from raw text.
- **Input**: Normalized description `string`, category `string`.
- **Output**: Key-Value `dictionary`.
- **Errors**: `ExtractionTimeoutError`, `SchemaValidationError`
- **Version**: `v2.0` (LLM backed)
- **Timeout**: 3000ms
- **Retry Behavior**: 2 retries (LLM latency mitigation).
- **Observability Metadata**: `token_count`, `model_name`, `temperature`

### 3.5 Classifier
Maps a material to the internal taxonomy tree.
- **Input**: Normalized description `string`, Extracted Attributes `dict`.
- **Output**: Classification `code`.
- **Errors**: `ClassificationConfidenceTooLow`
- **Version**: `v1.2`
- **Timeout**: 2000ms
- **Retry Behavior**: 1 retry.
- **Observability Metadata**: `top_3_candidates`, `confidence_scores`

### 3.6 EmbeddingGenerator
Converts text into a floating-point semantic array.
- **Input**: Canonical text representation `string`.
- **Output**: `List[float]` (dimension: config specific, e.g. 768).
- **Errors**: `EmbeddingServiceUnavailable`
- **Version**: `v1.0`
- **Timeout**: 2000ms
- **Retry Behavior**: 3 retries (remote API/GPU queue).
- **Observability Metadata**: `model_name`, `vector_dimension`

### 3.7 CandidateRetriever
Searches the database (via pgvector) for nearest neighbors.
- **Input**: Query embedding `List[float]`, `limit`, `threshold`.
- **Output**: List of `Candidate` objects.
- **Errors**: `DatabaseTimeoutError`
- **Version**: `v1.0`
- **Timeout**: 1000ms
- **Retry Behavior**: 1 retry.
- **Observability Metadata**: `index_used`, `search_duration_ms`

### 3.8 Matcher
Compares a query material against a retrieved candidate to determine match class.
- **Input**: Query `NormalizedMaterial`, Candidate `NationalMaterial`.
- **Output**: `MatchResult` (EXACT, NEAR, NOT_EQUIVALENT, etc.).
- **Errors**: `MatchingLogicError`
- **Version**: `v1.5`
- **Timeout**: 500ms
- **Retry Behavior**: None.
- **Observability Metadata**: `similarity_score`, `jaccard_score`

### 3.9 RuleEngine
Evaluates technical attributes against the `CriticalRules` registry (e.g. flagging mismatched pressure classes).
- **Input**: Attributes A `dict`, Attributes B `dict`, Category `string`.
- **Output**: List of `Conflict` objects.
- **Errors**: `RuleEvaluationError`
- **Version**: `v1.0`
- **Timeout**: 100ms
- **Retry Behavior**: None.
- **Observability Metadata**: `rules_evaluated_count`

### 3.10 RiskEngine
Determines if a match is safe to auto-approve based on similarity and conflicts.
- **Input**: `MatchResult`, List of `Conflict` objects.
- **Output**: Risk Level (`LOW`, `MEDIUM`, `HIGH`) and Action (`AUTO_APPROVE`, `MANUAL_REVIEW`).
- **Errors**: `RiskCalculationError`
- **Version**: `v1.0`
- **Timeout**: 100ms
- **Retry Behavior**: None.
- **Observability Metadata**: `risk_factors`

### 3.11 ExplanationGenerator
Uses an LLM to generate a human-readable justification for an AI decision.
- **Input**: `MatchResult`, Attributes, Conflicts.
- **Output**: Markdown explanation `string`.
- **Errors**: `LLMTimeoutError`
- **Version**: `v1.0`
- **Timeout**: 5000ms
- **Retry Behavior**: 1 retry.
- **Observability Metadata**: `prompt_tokens`, `completion_tokens`

### 3.12 LLMProvider
Abstract wrapper around OpenAI, Anthropic, or local vLLM instances.
- **Input**: Prompt `string`, System Message `string`.
- **Output**: Completion `string` or JSON.
- **Errors**: `RateLimitError`, `ProviderUnavailableError`
- **Version**: `v2.0`
- **Timeout**: 10000ms
- **Retry Behavior**: Exponential backoff (max 5 retries).
- **Observability Metadata**: `provider_name`, `model_name`, `latency_ms`

### 3.13 ERPAdapter
Maps raw ERP data (SAP/Oracle) into the platform's standard format.
- **Input**: ERP Payload `JSON/CSV`.
- **Output**: List of `SourceMaterial` objects.
- **Errors**: `SchemaMappingError`, `NetworkError`
- **Version**: `v1.0`
- **Timeout**: 30000ms
- **Retry Behavior**: 3 retries.
- **Observability Metadata**: `erp_source`, `records_parsed`, `records_failed`
