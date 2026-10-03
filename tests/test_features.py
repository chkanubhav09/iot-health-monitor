import importlib.util
import os
import pathlib
import sys

os.environ.setdefault("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:000000000000:test")
os.environ.setdefault("MODEL_BUCKET", "test-bucket")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(path):
    spec = importlib.util.spec_from_file_location("mod", ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_extract_features_order_and_defaults():
    mod = _load("backend/anomaly_detector/handler.py")
    out = mod.extract_features({"heart_rate": 80, "spo2": 97, "temperature": 37.0, "ecg_raw": 2100})
    assert out.shape == (1, 4)
    assert out[0].tolist() == [80.0, 97.0, 37.0, 2100.0]
    default = mod.extract_features({})
    assert default[0].tolist() == [72.0, 98.0, 36.8, 2048.0]


def test_training_pipeline_runs_on_sample_data():
    sys.path.insert(0, str(ROOT / "ml"))
    import pandas as pd
    import train

    df = pd.read_csv(train.DATA_PATH)
    model = train.build_pipeline()
    model.fit(df[train.FEATURES].values)
    preds = model.predict(df[train.FEATURES].values)
    assert set(preds.tolist()) <= {1, -1}
