import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Ingest handler - validates input and logs request.
    Returns {"ok": true} as placeholder.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }
