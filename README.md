# IoT Health Monitor

ESP32 (MicroPython) vitals node + AWS serverless pipeline with ML anomaly detection.

![MicroPython](https://img.shields.io/badge/MicroPython-ESP32-green) ![Python](https://img.shields.io/badge/Python-3.11-blue) ![AWS](https://img.shields.io/badge/AWS-IoT%20Core%20%7C%20Lambda%20%7C%20DynamoDB%20%7C%20SNS-orange) ![Terraform](https://img.shields.io/badge/IaC-Terraform-purple) ![License](https://img.shields.io/badge/License-MIT-yellow)

An ESP32 reads ECG, pulse/SpO2 and body temperature, publishes JSON over MQTT/TLS to AWS IoT Core, and a serverless backend validates and stores each reading and runs an Isolation Forest model that sends an SNS alert on anomalous vitals.

I built this as a learning project to connect embedded sensing with cloud and ML in one end-to-end design.

## Status (read this first)

- The firmware, Lambda functions, Terraform and CI are all in this repo and written end to end.
- The training data in `ml/data/sample_vitals.csv` is a **small synthetic set (30 rows, only 2 labelled anomalies)**, not real patient data. The F1 printed by `ml/train.py` is not a meaningful accuracy figure on this data.
- The SpO2 and heart-rate calculations in `firmware/sensors.py` are **simplified estimates** from raw MAX30100 readings. They are not calibrated and this is **not a medical device**.
- `battery_pct` in the payload is a placeholder value.
- No latency or accuracy benchmarks are claimed here.

## Architecture

```
[ESP32 + AD8232 + MAX30100 + DS18B20 + SSD1306 OLED]
                  |
          MQTT over TLS (8883)
                  |
            [AWS IoT Core]
                  |
              Topic Rule
             /          \
   [Lambda: validator]  [Lambda: anomaly detector]
            |                     |
        [DynamoDB]            [SNS alert]
```

## Hardware

| Component | Purpose | Interface |
|---|---|---|
| ESP32 (38-pin) | Microcontroller, Wi-Fi | - |
| AD8232 | ECG front end | ADC pin 34 |
| MAX30100 | Pulse and SpO2 | I2C (SDA 21, SCL 22) |
| DS18B20 | Body temperature | OneWire pin 4 |
| SSD1306 0.96" OLED | Local readout | I2C (SDA 21, SCL 22) |

## What each part does

- `firmware/` - MicroPython: reads the sensors every ~500 ms, publishes JSON to `health/<device_id>/vitals`, shows HR / SpO2 / temperature on the OLED, reconnects on connection errors.
- `backend/vitals_validator/` - Lambda: checks the payload schema and writes to DynamoDB (with TTL).
- `backend/anomaly_detector/` - Lambda: loads the model from S3, scores each reading, publishes an SNS alert if flagged.
- `ml/train.py` - trains a scikit-learn pipeline (StandardScaler + Isolation Forest) on `heart_rate`, `spo2`, `temperature`, `ecg_raw`, prints a classification report, optionally uploads the model to S3.
- `infra/` - Terraform for the IoT Thing, policy and topic rule, DynamoDB table, Lambdas, IAM and the SNS topic.
- `.github/workflows/ci.yml` - lint, tests, model training, `terraform validate`/plan on PRs, deploy on main.

## MQTT payload

```json
{
  "device_id": "esp32-patient-01",
  "seq": 0,
  "timestamp": 1712000000,
  "ecg_raw": 2048,
  "heart_rate": 72,
  "spo2": 98,
  "temperature": 36.8,
  "battery_pct": 85
}
```

## Setup

1. Clone the repo.
2. Edit `firmware/config.py` with your Wi-Fi details, AWS IoT endpoint and certificate paths. Never commit real credentials or certificates (`certs/` is git-ignored).
3. Flash MicroPython to the ESP32, then copy the firmware files with `ampy`:
   ```bash
   pip install esptool adafruit-ampy
   esptool.py --port /dev/ttyUSB0 erase_flash
   esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 <micropython.bin>
   ampy --port /dev/ttyUSB0 put firmware/config.py
   ampy --port /dev/ttyUSB0 put firmware/sensors.py
   ampy --port /dev/ttyUSB0 put firmware/main.py
   ```
   The OLED needs the `ssd1306` MicroPython module on the board.
4. Deploy the cloud side:
   ```bash
   cd infra
   terraform init
   terraform apply -var="alert_email=you@example.com" -var="model_bucket=<your-bucket>"
   ```
5. Train the model and upload it:
   ```bash
   pip install -r backend/requirements.txt
   python ml/train.py --s3-bucket <your-bucket>
   ```

## Known gaps / next steps

- Replace the estimated HR/SpO2 maths with a proper MAX30100 driver and calibration.
- Train on properly collected, labelled data instead of the synthetic sample.
- Add unit tests (the CI test job expects a `tests/` folder).
- Read battery voltage from an ADC instead of the placeholder.
- Add a dashboard on top of DynamoDB.

## License

MIT, see [LICENSE](LICENSE).
