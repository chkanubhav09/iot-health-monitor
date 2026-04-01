# firmware/config.py
# Configuration template for IoT Health Monitor
# IMPORTANT: Copy this file, fill in your values, and never commit secrets to git.
# The .gitignore already excludes certs/ and any file ending in _secret.*

# ── Wi-Fi ──────────────────────────────────────────────────────────────────────
WIFI_SSID     = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# ── AWS IoT Core ───────────────────────────────────────────────────────────────
# Endpoint from: AWS Console → IoT Core → Settings → Device data endpoint
AWS_ENDPOINT  = "xxxxxxxxxxxxxx-ats.iot.ap-south-1.amazonaws.com"
AWS_PORT      = 8883

# ── Device Identity ────────────────────────────────────────────────────────────
DEVICE_ID     = "esp32-patient-01"
MQTT_TOPIC    = f"health/{DEVICE_ID}/vitals"

# ── TLS Certificate Paths (on ESP32 filesystem) ────────────────────────────────
# Upload these files via ampy before running main.py:
#   ampy put certs/device.crt
#   ampy put certs/device.key
#   ampy put certs/AmazonRootCA1.pem
CLIENT_CERT   = "/certs/device.crt"
CLIENT_KEY    = "/certs/device.key"
CA_CERT       = "/certs/AmazonRootCA1.pem"
