"""
NewsFlow API Lambda — plain Python handler
Routes:
  OPTIONS *                       → CORS preflight
  GET  /newsflow-api/health       → health check
  GET  /newsflow-api/digest       → ranked summaries (deduped, date-filterable)
  GET  /newsflow-api/preferences  → user topic preferences
  PUT  /newsflow-api/preferences  → save user topic preferences

Query params for /digest:
  limit   int   max results (default 500)
  date    str   YYYY-MM-DD filter by generated_at date (optional)
"""
import json, os, hashlib
import boto3
from boto3.dynamodb.conditions import Attr

TABLE_SUMMARIES   = os.environ.get("TABLE_SUMMARIES",   "nf-summaries")
TABLE_PREFERENCES = os.environ.get("TABLE_PREFERENCES", "nf-preferences")

dynamodb        = boto3.resource("dynamodb")
tbl_summaries   = dynamodb.Table(TABLE_SUMMARIES)
tbl_preferences = dynamodb.Table(TABLE_PREFERENCES)

CORS_HEADERS = {
    "Content-Type":                 "application/json",
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Max-Age":       "300",
}

def _to_float(val):
    try:    return float(val)
    except: return 0.0

def _resp(body, status=200):
    return {"statusCode": status, "headers": CORS_HEADERS,
            "body": json.dumps(body, default=str)}

def _err(msg, status=400):
    return _resp({"error": msg}, status)

def _summary_hash(text):
    """Fingerprint first 120 chars of summary to detect duplicates."""
    return hashlib.md5((text or "")[:120].strip().lower().encode()).hexdigest()

def handle_digest(params):
    date_filter = params.get("date")  # YYYY-MM-DD or None
    raw_limit   = params.get("limit", 500)
    try:    limit = min(int(raw_limit), 500)
    except: limit = 500

    filter_expr = Attr("passed_gate").eq(True)
    result = tbl_summaries.scan(FilterExpression=filter_expr)
    items  = result.get("Items", [])
    while "LastEvaluatedKey" in result:
        result = tbl_summaries.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=result["LastEvaluatedKey"],
        )
        items.extend(result.get("Items", []))

    # Sort by score desc before dedup so we keep the highest-score copy
    items.sort(key=lambda x: _to_float(x.get("score", 0)), reverse=True)

    # ── Deduplicate by summary text fingerprint ───────────────────────────
    seen_hashes = set()
    deduped = []
    for item in items:
        h = _summary_hash(item.get("summary", ""))
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped.append(item)

    # ── Collect all available dates BEFORE date filter (needed for date picker) ─
    all_dates = sorted({
        item.get("generated_at", "")[:10]
        for item in deduped
        if item.get("generated_at", "")[:10]
    }, reverse=True)

    # ── Date filter ───────────────────────────────────────────────────────
    if date_filter:
        deduped = [
            item for item in deduped
            if item.get("generated_at", "")[:10] == date_filter
        ]

    # Convert Decimal fields and add digest_date convenience field
    for item in deduped:
        for field in ("score", "relevance", "authority", "recency"):
            if field in item:
                item[field] = str(round(_to_float(item[field]), 4))
        item["digest_date"] = item.get("generated_at", "")[:10]

    return _resp({
        "digest":     deduped[:limit],
        "total":      len(deduped),
        "dates":      all_dates,       # dates that have digest data
    })

def handle_get_preferences(params):
    user_id = params.get("user_id")
    if not user_id:
        return _err("user_id required")
    result = tbl_preferences.get_item(Key={"user_id": str(user_id)})
    item   = result.get("Item")
    if not item:
        return _resp({"onboarded": False, "topics": []})
    return _resp({
        "onboarded": bool(item.get("onboarded", False)),
        "topics":    list(item.get("topics", [])),
    })

def handle_put_preferences(body_raw):
    try:    body = json.loads(body_raw or "{}")
    except: return _err("invalid JSON")
    user_id   = body.get("user_id")
    topics    = body.get("topics", [])
    onboarded = body.get("onboarded", True)
    if not user_id:                    return _err("user_id required")
    if not isinstance(topics, list):   return _err("topics must be array")
    if not isinstance(onboarded, bool):return _err("onboarded must be bool")
    tbl_preferences.put_item(Item={
        "user_id": str(user_id), "onboarded": onboarded, "topics": topics,
    })
    return _resp({"ok": True})

def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()
    path   = event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}
    body   = event.get("body") or ""

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}
    if path.endswith("/health"):
        return _resp({"status": "ok"})
    if path.endswith("/digest"):
        return handle_digest(params) if method == "GET" else _err("method not allowed", 405)
    if path.endswith("/preferences"):
        if method == "GET": return handle_get_preferences(params)
        if method == "PUT": return handle_put_preferences(body)
        return _err("method not allowed", 405)
    return _err("not found", 404)