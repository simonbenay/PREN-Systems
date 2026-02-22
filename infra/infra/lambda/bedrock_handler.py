"""
Bedrock handler — structure le texte extrait par Textract en signaux JSON normalisés.
Utilise Amazon Nova Micro (eu.amazon.nova-micro-v1:0) via l'API Converse.
"""
import json
import logging
import os
import boto3
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SIGNALS_TABLE = os.environ.get("SIGNALS_TABLE", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.amazon.nova-micro-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name="eu-west-3")
dynamodb = boto3.resource("dynamodb")
signals_table = dynamodb.Table(SIGNALS_TABLE) if SIGNALS_TABLE else None

STRUCTURING_PROMPT = """Tu es un expert en analyse immobiliere et urbanisme.
Analyse le texte suivant extrait d'un document municipal ({doc_type}) pour la ville de {city}.

Extrais les signaux immobiliers sous forme de JSON structure.
Reponds UNIQUEMENT avec du JSON valide, sans texte avant ou apres, sans markdown.

Format attendu :
{{
  "signals": [
    {{
      "type": "permit|zoning|infrastructure|renovation|commercial",
      "description": "description courte du signal en francais",
      "impact": "positive|negative|neutral",
      "confidence": 0.0,
      "location_hint": "quartier ou zone mentionne si disponible"
    }}
  ],
  "summary": "resume en 1-2 phrases du document",
  "signal_count": 0
}}

Texte a analyser :
{text}
"""


def _parse_nova_json(raw: str) -> dict:
    """Nettoie et parse la sortie JSON de Nova (retire les backticks si présents)."""
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:]) if len(lines) > 1 else clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    return json.loads(clean.strip())


def handler(event, context):
    """
    Input event (depuis textract_handler output) :
    {
      "s3_key": "pdfs/xxx.pdf",
      "doc_type": "zoning",
      "city": "Paris",
      "extracted_text": "...",
      "page_count": 1,
      "extraction_method": "textract"
    }
    """
    logger.info("Bedrock structuring request")

    # Accepte l'event directement ou encapsulé dans body (Step Functions)
    if "body" in event and isinstance(event["body"], str):
        payload = json.loads(event["body"])
    else:
        payload = event

    extracted_text = payload.get("extracted_text", "")
    doc_type = payload.get("doc_type", "unknown")
    city = payload.get("city", "Paris")
    s3_key = payload.get("s3_key", "")

    if not extracted_text:
        return {"statusCode": 400, "body": json.dumps({"error": "extracted_text required"})}

    prompt = STRUCTURING_PROMPT.format(
        doc_type=doc_type,
        city=city,
        text=extracted_text[:5000]
    )

    # Appel Nova via API Converse
    try:
        response = bedrock.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 2000, "temperature": 0.1}
        )
        raw_output = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})
        logger.info(f"Nova tokens: input={usage.get('inputTokens')} output={usage.get('outputTokens')}")
    except Exception as e:
        logger.error(f"Bedrock error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": f"Bedrock failed: {e}"})}

    # Parser le JSON
    try:
        structured = _parse_nova_json(raw_output)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed: {raw_output[:300]}")
        structured = {"signals": [], "summary": "Parsing failed", "signal_count": 0, "raw": raw_output[:500]}

    # Stocker les signaux dans DynamoDB
    stored = 0
    if signals_table and structured.get("signals"):
        timestamp = datetime.utcnow().isoformat()
        for i, signal in enumerate(structured["signals"][:10]):
            try:
                signals_table.put_item(Item={
                    "pk": f"DOC#{s3_key}",
                    "sk": f"SIGNAL#{i:03d}",
                    "doc_type": doc_type,
                    "city": city,
                    "signal_type": signal.get("type", "unknown"),
                    "description": signal.get("description", ""),
                    "impact": signal.get("impact", "neutral"),
                    "confidence": str(signal.get("confidence", 0.5)),
                    "location_hint": signal.get("location_hint", ""),
                    "created_at": timestamp
                })
                stored += 1
            except Exception as e:
                logger.error(f"DynamoDB write error: {e}")

    logger.info(f"Structured {len(structured.get('signals', []))} signals, stored {stored} in DynamoDB")

    result = {
        "s3_key": s3_key,
        "doc_type": doc_type,
        "city": city,
        "structured_signals": structured,
        "signals_stored": stored,
        "model_id": BEDROCK_MODEL_ID,
        "status": "structured"
    }
    return {"statusCode": 200, "body": json.dumps(result)}
