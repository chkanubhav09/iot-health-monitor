# firmware/main.py
# ESP32 MicroPython - IoT Health Monitor
# Publishes ECG, SpO2, HR, and Temperature to AWS IoT Core via MQTT/TLS

import time
import json
import ubinascii
from machine import Pin, I2C, ADC
from umqtt.simple import MQTTClient
import network
from sensors import ECGSensor, PulseOximeter, TempSensor, OLEDDisplay
from config import (
    WIFI_SSID, WIFI_PASSWORD,
    AWS_ENDPOINT, AWS_PORT,
    DEVICE_ID, MQTT_TOPIC,
    CLIENT_CERT, CLIENT_KEY, CA_CERT
)

# ---------- Wi-Fi ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        print("Wi-Fi connected:", wlan.ifconfig()[0])
    else:
        raise RuntimeError("Wi-Fi connection failed")

# ---------- MQTT ----------
def connect_mqtt():
    client = MQTTClient(
        client_id=DEVICE_ID,
        server=AWS_ENDPOINT,
        port=AWS_PORT,
        keepalive=60,
        ssl=True,
        ssl_params={
            "certfile": CLIENT_CERT,
            "keyfile":  CLIENT_KEY,
            "cafile":   CA_CERT,
        }
    )
    client.connect()
    print("MQTT connected to", AWS_ENDPOINT)
    return client

# ---------- Main Loop ----------
def main():
    connect_wifi()
    
    ecg     = ECGSensor(adc_pin=34)
    pulse   = PulseOximeter()          # MAX30100 over I2C
    temp    = TempSensor(data_pin=4)   # DS18B20 OneWire
    display = OLEDDisplay()            # SSD1306 OLED
    
    client = connect_mqtt()
    
    print("Starting sensor loop (500 ms interval)...")
    seq = 0
    
    while True:
        try:
            ecg_val  = ecg.read_raw()
            hr, spo2 = pulse.read()
            temp_c   = temp.read_celsius()
            battery  = 85  # placeholder — hook up ADC on production hardware
            
            payload = json.dumps({
                "device_id":  DEVICE_ID,
                "seq":        seq,
                "timestamp":  time.time(),
                "ecg_raw":    ecg_val,
                "heart_rate": hr,
                "spo2":       spo2,
                "temperature": temp_c,
                "battery_pct": battery,
            })
            
            client.publish(MQTT_TOPIC, payload)
            
            # Local OLED display
            display.show(hr=hr, spo2=spo2, temp=temp_c)
            
            print(f"[{seq}] HR={hr} SpO2={spo2}% Temp={temp_c}C ECG={ecg_val}")
            seq += 1
            time.sleep_ms(500)
            
        except OSError as e:
            print("Connection error:", e)
            client = connect_mqtt()  # reconnect

if __name__ == "__main__":
    main()
