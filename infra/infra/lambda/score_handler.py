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
    # HTTP API (payload v2) provides queryStringParameters dict
    q = event.get("queryStringParameters") or {}
    lat = q.get("lat")
    lng = q.get("lng")
    return lat, lng


def _demo_iris_from_latlng(lat: float, lng: float) -> str:
    """
    Simple demo mapping for Paris:
    - Higher lat: PARIS_DEMO_1
    - Else higher lng: PARIS_DEMO_2
    - Else: PARIS_DEMO_3
    """
    if lat >= 48.86:
        return "PARIS_DEMO_1"
    if lng >= 2.36:
        return "PARIS_DEMO_2"
    return "PARIS_DEMO_3"


def handler(event, context):
    logger.info(f"Score request: {json.dumps(event)}")

    if not table:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "SCORES_TABLE not configured", "intended_use": INTENDED_USE}),
        }

    lat_s, lng_s = _parse_query_params(event)
    if lat_s is None or lng_s is None:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": "Missing query parameters. Provide lat and lng.",
                    "example": "/score?lat=48.8566&lng=2.3522",
                    "intended_use": INTENDED_USE,
                }
            ),
        }

    try:
        lat = float(lat_s)
        lng = float(lng_s)
    except ValueError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": "lat/lng must be numbers", "intended_use": INTENDED_USE}
            ),
        }

    iris_id = _demo_iris_from_latlng(lat, lng)

    resp = table.get_item(Key={"iris_id": iris_id})
    item = resp.get("Item")

    if not item:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": "No score found for iris_id",
                    "iris_id": iris_id,
                    "intended_use": INTENDED_USE,
                }
            ),
        }

    # Convert Decimals and present nicer output
    out = {
        "iris_id": item.get("iris_id"),
        "city": item.get("city", "Paris"),
        "future_value_score": _to_float(item.get("future_value_score")),
        "momentum": item.get("momentum"),
        "confidence": _to_float(item.get("confidence")),
        "data_freshness_days": _to_float(item.get("data_freshness_days")),
        "top_signals": [s.strip() for s in (item.get("top_signals", "")).split(";") if s.strip()],
        "updated_at": item.get("updated_at"),
        "intended_use": INTENDED_USE,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(out),
    }
