# PREN — Predictive Real Estate Nexus (PREN Lite / Paris Pilot MVP)

PREN is an AI-driven predictive platform that forecasts **real estate value** and **neighborhood gentrification signals** up to **5 years ahead** using “silent signals” such as **zoning/permitting activity** and **infrastructure plans** (with optional privacy-safe aggregated sentiment later).

This repository contains **PREN Lite**, a **Paris pilot MVP** built on a **serverless AWS stack** with:
- a simple scoring API (`/score`)
- an explainability endpoint (`/explain`)
- a smoke-test endpoint (`/health`)
- an ingestion workflow placeholder (Step Functions)
- monitoring (CloudWatch alarm on API 5XX)

> **Intended use (ethical guardrail):** planning & risk management for banks, brokers, and developers.  
> **Not intended for:** discriminatory decisions or speculative targeting that could accelerate displacement.

---

## AWS 10,000 AIdeas Competition (Building Phase)

Built for the **AWS 10,000 AIdeas Competition** as part of the **Building Phase**.

- **Team:** PREN Systems  
- **Category:** Commercial Solutions  
- **Pilot city:** Paris (Lyon planned as scalability follow-up)

**What’s implemented now (PREN Lite):**
- Deployed serverless backend (API Gateway + Lambda + DynamoDB + Step Functions + S3)
- Explainable score responses with **limitations**, **ethics**, and **roadmap**
- Health endpoint for end-to-end checks
- CloudWatch alarm for API 5XX errors

**Planned next (aligned with the original idea):**
- **Textract** for municipal PDFs → structured signal extraction  
- **Bedrock (batch)** for synthesis/normalization of unstructured “silent signals” (cost-optimized)  
- **SageMaker (batch)** to produce the 5-year **Future Value Score** + bias audits (Clarify)

---

## Live Demo (deployed)

**Base URL**  
`https://7nskojt600.execute-api.eu-west-3.amazonaws.com/`

### 1) Score — Future Value Score
Example:
- `GET /score?lat=48.8566&lng=2.3522`

Returns a demo **Future Value Score** and IRIS-level pilot fields.

### 2) Explain — Why the score?
Examples:
- `GET /explain?iris_id=PARIS_DEMO_3`
- `GET /explain?lat=48.8566&lng=2.3522`

Returns:
- summary (“why this score”)
- top signals (demo)
- limitations
- ethics & intended use
- next steps + roadmap

### 3) Health — End-to-end smoke test
Example:
- `GET /health`

Validates the system can read a known demo score item in DynamoDB.

---

## Architecture (PREN Lite)

**Region:** eu-west-3 (Paris)

**Core components:**
- **API Gateway (HTTP API)** routes: `/score`, `/explain`, `/health`
- **AWS Lambda (Python 3.11)**:
  - `score_handler.py`
  - `explain_handler.py`
  - `health_handler.py`
- **Amazon DynamoDB**
  - Scores table with demo items: `PARIS_DEMO_1`, `PARIS_DEMO_2`, `PARIS_DEMO_3`
  - Signals table reserved for ingestion features
- **AWS Step Functions**
  - `PrenIngestionStateMachine` (demo ingestion flow placeholder)
- **Amazon S3**
  - Raw bucket (PDFs/datasets)
  - Artifacts bucket (batch outputs)
- **Amazon CloudWatch**
  - Logs (7-day retention)
  - Alarm on HTTP API **5XX errors** (prod-minded monitoring)

---

## Cost & Safety Notes

- Serverless + DynamoDB **PAY_PER_REQUEST** keeps costs low for an MVP.
- Log retention is limited (7 days) for cost control.
- No individual-level personal data is processed in this MVP.
- Sentiment is **OFF by design** for privacy and bias control (RGPD-aware approach later).

---

## Roadmap (toward full PREN platform)

- **Geo layer:** replace demo mapping with real **IRIS lookup** + optional **500m grid** (Paris → Lyon scalability).
- **Ingestion pipeline:** **Textract** (PDF) → **Bedrock batch** structuring into normalized signals (cost-optimized).
- **Scoring pipeline:** **SageMaker batch inference** + drift monitoring + **bias audit (Clarify)** for gentrification risk.
- **Optional:** privacy-safe aggregated sentiment (opt-in, RGPD-aware) with low weight in the model.

---

## Repo Structure

- `infra/` — AWS CDK (Python) stack + Lambda handlers
- `docs/` — specs / notes used for the competition article

---

## License

MIT (add a `LICENSE` file if you want to make this explicit).
