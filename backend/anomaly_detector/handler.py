# backend/anomaly_detector/handler.py
# AWS Lambda: Isolation Forest anomaly detection -> SNS alert

import json
import os
import pickle
import boto3
import numpy as np

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
MODEL_PATH    = "/tmp/model.pkl"
S3_BUCKET     = os.environ["MODEL_BUCKET"]
S3_KEY        = os.environ.get("MODEL_KEY", "models/isolation_forest.pkl")

_model = None  # module-level cache for Lambda warm starts

s3  = boto3.client("s3")
sns = boto3.client("sns")


def load_model():
    global _model
    if _model is None:
        print(f"Downloading model from s3://{S3_BUCKET}/{S3_KEY}")
        s3.download_file(S3_BUCKET, S3_KEY, MODEL_PATH)
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
        print("Model loaded.")
    return _model


def extract_features(payload: dict) -> np.ndarray:
    """Extract numeric feature vector from vitals payload."""
    return np.array([[
        float(payload.get("heart_rate",   72)),
        float(payload.get("spo2",         98)),
        float(payload.get("temperature",  36.8)),
        float(payload.get("ecg_raw",      2048)),
    ]])


def lambda_handler(event, context):
    """
    Triggered by DynamoDB Streams or IoT Rule.
    Runs Isolation Forest and publishes SNS alert if anomaly detected.
    """
    print("Event:", json.dumps(event))

    model    = load_model()
    features = extract_features(event)
    score    = model.decision_function(features)[0]  # negative = more anomalous
    pred     = model.predict(features)[0]             # -1 = anomaly, 1 = normal

    print(f"Anomaly score: {score:.4f}  prediction: {pred}")

    if pred == -1:
        device_id = event.get("device_id", "unknown")
        message   = (
            f"ALERT: Anomalous vitals detected!\n"
            f"Device  : {device_id}\n"
            f"HR      : {event.get('heart_rate')} bpm\n"
            f"SpO2    : {event.get('spo2')} %\n"
            f"Temp    : {event.get('temperature')} C\n"
            f"ECG raw : {event.get('ecg_raw')}\n"
            f"Score   : {score:.4f}"
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Health Alert - {device_id}",
            Message=message,
        )
        print("SNS alert sent.")
        return {"anomaly": True, "score": score}

    return {"anomaly": False, "score": score}
