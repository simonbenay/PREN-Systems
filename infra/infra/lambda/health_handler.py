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


def handler(event, context):
    logger.info("Health check request received")

    if not table:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "FAIL", "reason": "SCORES_TABLE not set", "intended_use": INTENDED_USE}),
        }

    iris_id = "PARIS_DEMO_3"
    resp = table.get_item(Key={"iris_id": iris_id})
    item = resp.get("Item")

    if not item:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "FAIL", "reason": f"Missing item {iris_id}", "intended_use": INTENDED_USE}),
        }

    required = ["future_value_score", "confidence", "momentum", "updated_at"]
    missing = [k for k in required if k not in item]
    if missing:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "FAIL", "reason": "Missing fields", "missing": missing, "intended_use": INTENDED_USE}),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "PASS",
                "checked_iris_id": iris_id,
                "future_value_score": _to_float(item.get("future_value_score")),
                "confidence": _to_float(item.get("confidence")),
                "intended_use": INTENDED_USE,
            }
        ),
    }
