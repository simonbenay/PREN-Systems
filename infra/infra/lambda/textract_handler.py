"""
Textract handler — extrait le texte d'un PDF depuis S3.
Stratégie :
  1. Textract DetectDocumentText (synchrone, recommandé si activé)
  2. Fallback pypdf (pure Python) si Textract non disponible sur ce compte
"""
import io
import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RAW_BUCKET = os.environ.get("RAW_BUCKET", "")
SIGNALS_TABLE = os.environ.get("SIGNALS_TABLE", "")

textract = boto3.client("textract", region_name="eu-west-3")

# AnalyzeDocument feature types valides pour l'extraction de texte PLU
_ANALYZE_FEATURES = ["TABLES"]
s3_client = boto3.client("s3", region_name="eu-west-3")
dynamodb = boto3.resource("dynamodb")
signals_table = dynamodb.Table(SIGNALS_TABLE) if SIGNALS_TABLE else None


def _extract_with_pypdf(s3_bucket: str, s3_key: str) -> tuple[list[str], int]:
    """Fallback : télécharge le PDF depuis S3 et extrait le texte avec pypdf."""
    logger.info(f"Fallback pypdf pour s3://{s3_bucket}/{s3_key}")
    obj = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    pdf_bytes = obj["Body"].read()

    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    lines = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines.append(line)
    return lines, len(reader.pages)


def handler(event, context):
    """
    Input event:
    {
      "s3_bucket": "...",
      "s3_key": "pdfs/plu_paris_zone1.pdf",
      "doc_type": "zoning",
      "city": "Paris"
    }
    """
    logger.info(f"Textract request: {json.dumps(event)}")

    s3_bucket = event.get("s3_bucket", RAW_BUCKET)
    s3_key = event.get("s3_key", "")
    doc_type = event.get("doc_type", "unknown")
    city = event.get("city", "Paris")

    if not s3_key:
        return {"statusCode": 400, "body": json.dumps({"error": "s3_key required"})}

    extraction_method = "textract"
    lines = []
    page_count = 0

    # Tentative Textract AnalyzeDocument (synchrone, supporte PDF)
    try:
        response = textract.analyze_document(
            Document={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
            FeatureTypes=_ANALYZE_FEATURES
        )
        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block["Text"])
        page_count = len(set(b.get("Page", 1) for b in response.get("Blocks", [])))
        logger.info(f"Textract AnalyzeDocument OK : {len(lines)} lignes, {page_count} pages")

    except ClientError as e:
        code = e.response["Error"]["Code"]
        logger.warning(f"Textract indisponible ({code}) — bascule sur pypdf")
        if code in ("SubscriptionRequiredException", "AccessDeniedException",
                    "UnsupportedDocumentException", "InvalidParameterException"):
            try:
                lines, page_count = _extract_with_pypdf(s3_bucket, s3_key)
                extraction_method = "pypdf"
                logger.info(f"pypdf OK : {len(lines)} lignes, {page_count} pages")
            except Exception as pypdf_err:
                logger.error(f"pypdf error: {pypdf_err}")
                return {"statusCode": 500, "body": json.dumps({"error": f"Both extractors failed: {pypdf_err}"})}
        else:
            logger.error(f"Textract error inattendue: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    full_text = "\n".join(lines)
    result = {
        "s3_key": s3_key,
        "doc_type": doc_type,
        "city": city,
        "page_count": page_count,
        "line_count": len(lines),
        "extracted_text": full_text[:10000],  # Limiter pour le payload Step Functions
        "extraction_method": extraction_method,
        "status": "extracted"
    }

    logger.info(f"Extraction terminée ({extraction_method}) : {len(lines)} lignes, {page_count} pages")
    return {"statusCode": 200, "body": json.dumps(result)}
