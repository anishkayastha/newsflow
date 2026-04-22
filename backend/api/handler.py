import json
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr

TABLE_SUMMARIES = os.environ.get("TABLE_SUMMARIES", "nf-summaries")
dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(TABLE_SUMMARIES)


def _to_str(val):
    try:
        return str(round(float(val), 4))
    except Exception:
        return str(val)


def _clean(item):
    for field in ("score", "relevance", "authority", "recency"):
        if field in item:
            item[field] = _to_str(item[field])
    if "article_count" in item:
        item["article_count"] = int(item["article_count"])
    return item


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path   = event.get("rawPath", "/")

    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Authorization,Content-Type",
        "Access-Control-Max-Age": "300",
    }

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    if path.endswith("/health"):
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"status": "ok"})
        }

    if path.endswith("/digest") or path == "/":
        params   = event.get("queryStringParameters") or {}
        category = params.get("category")
        limit    = int(params.get("limit", 100))

        filt = Attr("passed_gate").eq(True)
        if category:
            filt = filt & Attr("topic").eq(category)

        result = table.scan(FilterExpression=filt)
        items  = result.get("Items", [])
        while "LastEvaluatedKey" in result:
            result = table.scan(
                FilterExpression=filt,
                ExclusiveStartKey=result["LastEvaluatedKey"]
            )
            items.extend(result.get("Items", []))

        items.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
        items = [_clean(i) for i in items[:limit]]

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"digest": items, "total": len(items)})
        }

    return {
        "statusCode": 404,
        "headers": headers,
        "body": json.dumps({"message": "not found"})
    }