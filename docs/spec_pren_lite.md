# PREN Lite MVP — Spec (PREN Systems)

## Context
Project for AWS 10,000 AIdeas Competition (Building Phase).
Team: PREN Systems
Category: Commercial Solutions
City pilot: Paris (primary) + Lyon (secondary scalability test)
Zones: IRIS (core) + 500m grid overlay
Sentiment: OFF for MVP (privacy + bias + cost guardrail)

## Goal
Build a demo-ready predictive platform that forecasts:
- 5-year Future Value Score (0–100)
- Gentrification Momentum (Low/Med/High)
Using "silent signals" from permits/zoning/infrastructure documents and open datasets.
Provide explainability and an enterprise API.

## MVP User journeys
1) Batch ingestion: process 50–200 municipal PDFs (Paris) -> extract -> structure signals -> store
2) Query a location (lat/lng) -> map to 500m grid -> IRIS -> return score + explanations
3) Enterprise API: /score returns JSON for underwriting workflows + ethical disclaimer
4) Explainability: /explain + AgentCore "Explain my score" generates a business-friendly explanation using only stored facts

## Architecture (AWS eu-west-3)
- S3: raw PDFs + batch outputs
- Step Functions + Lambda: orchestration
- Textract: PDF text extraction (limited volume)
- Bedrock: JSON structuring + summaries (BATCH-FIRST)
- DynamoDB: signals, features, scores
- SageMaker: training + batch scoring (no realtime endpoint)
- API Gateway + Lambda: /score and /explain
- CloudWatch: logs/metrics/alarms
- Bedrock AgentCore: explanation agent (no hallucination rule)

## Data sources (MVP)
- IRIS geometry (INSEE/IGN contours)
- Permits/authorizations (SITADEL/SDES open data)
- OpenStreetMap infrastructure/POIs (with attribution)
- Urban Atlas land use (optional)
- Filosofi IRIS socioeconomic context (optional, for bias audit + context only)

## Signal schema (v1)
Each processed document yields:
- doc_id (S3)
- doc_type (permit/zoning/infrastructure)
- date_issued
- location mapping (IRIS_id and/or geometry)
- signals[]: {type, value, unit, confidence, evidence_span}
- summary
- extraction_meta (pages, model, version)

## Guardrails
Cost:
- batch-first Bedrock + batch scoring SageMaker
- limit docs 50–200
- max 1 retry on invalid JSON
- budgets/alerts already configured
Ethics:
- no individual-level data
- no protected attributes
- disclaimers in API + UI: planning & risk management, not discrimination/speculative targeting
Quality:
- JSON schema validation required before storage
- low-quality PDFs flagged and excluded from training

## Deliverables (by Mar 13, 2026 20:00 UTC)
- Working pipeline (S3 -> Textract -> Bedrock batch -> DynamoDB)
- Feature aggregation per IRIS + scoring batch (SageMaker)
- API endpoints: /score, /explain
- Minimal UI (map + details)
- Demo assets (5 screenshots + <5 min video)
- Builder Center article compliant + evidence of Kiro usage (screenshots)
