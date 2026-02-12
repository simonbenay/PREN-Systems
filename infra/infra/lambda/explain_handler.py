import json
import logging
import os
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SCORES_TABLE = os.environ.get("SCORES_TABLE", "")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(SCORES_TABLE) if SCORES_TABLE else None

INTENDED_USE = "For planning & risk management; not for discriminatory decisions or speculative targeting."


def _to_float(x):
    if isinstance(x, Decimal):
        return float(x)
    return x


def _parse_query_params(event):
    q = event.get("queryStringParameters") or {}
    return q


def _demo_iris_from_latlng(lat: float, lng: float) -> str:
    # same logic as score_handler (keep consistent)
    if lat >= 48.86:
        return "PARIS_DEMO_1"
    if lng >= 2.36:
        return "PARIS_DEMO_2"
    return "PARIS_DEMO_3"


def handler(event, context):
    logger.info(f"Explain request: {json.dumps(event)}")

    if not table:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "SCORES_TABLE not configured", "intended_use": INTENDED_USE}),
        }

    q = _parse_query_params(event)
    iris_id = q.get("iris_id")

    # Allow explain by lat/lng for convenience (same as /score)
    if not iris_id:
        lat_s = q.get("lat")
        lng_s = q.get("lng")
        if lat_s and lng_s:
            try:
                lat = float(lat_s)
                lng = float(lng_s)
                iris_id = _demo_iris_from_latlng(lat, lng)
            except ValueError:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "lat/lng must be numbers", "intended_use": INTENDED_USE}),
                }

    if not iris_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": "Provide iris_id or lat/lng",
                    "examples": [
                        "/explain?iris_id=PARIS_DEMO_3",
                        "/explain?lat=48.8566&lng=2.3522",
                    ],
                    "intended_use": INTENDED_USE,
                }
            ),
        }

    resp = table.get_item(Key={"iris_id": iris_id})
    item = resp.get("Item")

    if not item:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "No score found", "iris_id": iris_id, "intended_use": INTENDED_USE}),
        }

    score = _to_float(item.get("future_value_score"))
    momentum = item.get("momentum")
    confidence = _to_float(item.get("confidence"))
    freshness = _to_float(item.get("data_freshness_days"))
    top_signals_raw = item.get("top_signals", "")
    top_signals = [s.strip() for s in top_signals_raw.split("|") if s.strip()]

    # Short, enterprise-friendly explanation
    explanation = {
        "summary": f"{iris_id} shows {momentum} momentum with a 5-year Future Value Score of {score}.",
        "why": [
            "Signals were aggregated at IRIS-level (pilot: Paris) and converted into a structured feature set.",
            f"Confidence ({confidence}) reflects data volume + signal consistency; freshness is ~{freshness} days.",
        ],
        "top_signals": top_signals,
        "limitations": [
            "This is an MVP demo: limited documents and simplified geo-mapping.",
            "No individual-level data; sentiment is OFF by design for privacy and bias control.",
            "Scores are decision-support signals, not a guarantee of future market outcomes.",
        ],
        "ethics": [
            "Use for planning and risk management (banks, brokers, developers).",
            "Not intended for discriminatory decisions or speculative targeting that could accelerate displacement.",
        ],
        "next_steps": [
            "Replace demo geo-mapping with real IRIS + 500m grid lookup.",
            "Ingestion pipeline: Textract -> Bedrock batch structuring -> DynamoDB signals.",
            "Scoring pipeline: SageMaker batch inference + bias audit (Clarify) for gentrification risk.",
        ],
        # ✅ NEW: roadmap (short, practical, article-friendly)
        "roadmap": [
            "Integrate real IRIS lookup + optional 500m grid for custom geo queries (Paris -> Lyon scalability).",
            "Ingestion: Textract (PDF) -> Bedrock batch structuring into normalized signals (cost-optimized).",
            "Scoring: SageMaker batch inference + drift monitoring + bias audit (Clarify) for gentrification risk.",
            "Optional: privacy-safe aggregated sentiment (opt-in, RGPD-aware) with low weight in the model.",
        ],
    }

    out = {
        "iris_id": iris_id,
        "city": item.get("city", "Paris"),
        "future_value_score": score,
        "momentum": momentum,
        "confidence": confidence,
        "data_freshness_days": freshness,
        "updated_at": item.get("updated_at"),
        "intended_use": INTENDED_USE,
        "explanation": explanation,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(out),
    }
