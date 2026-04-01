# backend/vitals_validator/handler.py
# AWS Lambda: validates incoming vitals payload and writes to DynamoDB

import json
import os
import time
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(os.environ["VITALS_TABLE"])

# Clinical alert thresholds
THRESHOLDS = {
    "heart_rate":   {"min": 40,  "max": 180},
    "spo2":         {"min": 88,  "max": 100},
    "temperature":  {"min": 35.0, "max": 39.5},
    "ecg_raw":      {"min": 0,   "max": 4095},
}

REQUIRED_FIELDS = {"device_id", "timestamp", "ecg_raw", "heart_rate", "spo2", "temperature"}


def validate(payload: dict) -> list:
    """Return list of validation errors (empty = valid)."""
    errors = []
    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        errors.append(f"Missing fields: {missing}")
        return errors  # no point checking values if fields are absent

    for field, bounds in THRESHOLDS.items():
        val = payload.get(field)
        if val is None:
            continue
        if not (bounds["min"] <= float(val) <= bounds["max"]):
            errors.append(
                f"{field}={val} outside [{bounds['min']}, {bounds['max']}]"
            )
    return errors


def lambda_handler(event, context):
    """
    Triggered by AWS IoT Core Topic Rule.
    Event is the raw MQTT payload (already parsed to dict by IoT Rule).
    """
    print("Received:", json.dumps(event))

    errors = validate(event)
    if errors:
        print("Validation failed:", errors)
        return {"statusCode": 400, "body": json.dumps({"errors": errors})}

    # Convert floats to Decimal for DynamoDB
    item = {
        k: Decimal(str(v)) if isinstance(v, float) else v
        for k, v in event.items()
    }
    item["ttl"] = int(time.time()) + 90 * 24 * 3600  # 90-day TTL
    item["ingested_at"] = int(time.time() * 1000)    # ms epoch

    table.put_item(Item=item)
    print(f"Stored vitals for device={item['device_id']} seq={item.get('seq')}")

    return {"statusCode": 200, "body": json.dumps({"stored": True})}
