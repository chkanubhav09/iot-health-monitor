# ml/train.py
# Train an Isolation Forest model on synthetic vitals data
# and upload the serialized model to S3 for Lambda inference.

import argparse
import os
import pickle
import pathlib

import boto3
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

DATA_PATH   = pathlib.Path(__file__).parent / "data" / "sample_vitals.csv"
MODEL_PATH  = pathlib.Path(__file__).parent / "model.pkl"
FEATURES    = ["heart_rate", "spo2", "temperature", "ecg_raw"]
CONTAMINATION = 0.05  # ~5% of training data are anomalies


def load_data(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows from {path}")
    return df


def build_pipeline(contamination: float = CONTAMINATION) -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("iso_forest", IsolationForest(
            n_estimators=200,
            contamination=contamination,
            max_features=len(FEATURES),
            random_state=42,
            n_jobs=-1,
        )),
    ])


def evaluate(model, X_test, y_test):
    """y_test: 1 = normal, -1 = anomaly (Isolation Forest convention)."""
    preds = model.predict(X_test)
    # Convert to binary: 1 = anomaly, 0 = normal  (for standard metrics)
    y_bin   = (y_test  == -1).astype(int)
    p_bin   = (preds   == -1).astype(int)
    f1 = f1_score(y_bin, p_bin, zero_division=0)
    print("\nClassification Report:")
    print(classification_report(y_bin, p_bin, target_names=["normal", "anomaly"]))
    print(f"F1 Score (anomaly class): {f1:.4f}")
    return f1


def upload_to_s3(model_path: pathlib.Path, bucket: str, key: str):
    s3 = boto3.client("s3")
    s3.upload_file(str(model_path), bucket, key)
    print(f"Model uploaded to s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="Train Isolation Forest on vitals data")
    parser.add_argument("--data",          default=str(DATA_PATH))
    parser.add_argument("--contamination", type=float, default=CONTAMINATION)
    parser.add_argument("--s3-bucket",     default=os.getenv("MODEL_BUCKET", ""))
    parser.add_argument("--s3-key",        default="models/isolation_forest.pkl")
    args = parser.parse_args()

    df = load_data(pathlib.Path(args.data))
    X  = df[FEATURES].values

    # Synthetic labels: rows flagged as anomaly in CSV column (if present)
    if "label" in df.columns:
        y = df["label"].map({"normal": 1, "anomaly": -1}).values
    else:
        y = np.ones(len(X), dtype=int)  # all normal for unsupervised training

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=(y if -1 in y else None)
    )

    print(f"Training on {len(X_train)} samples...")
    model = build_pipeline(args.contamination)
    model.fit(X_train)

    evaluate(model, X_test, y_test)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved to {MODEL_PATH}")

    if args.s3_bucket:
        upload_to_s3(MODEL_PATH, args.s3_bucket, args.s3_key)


if __name__ == "__main__":
    main()
