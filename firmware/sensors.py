# firmware/sensors.py
# Sensor drivers for AD8232 ECG, MAX30100 SpO2/HR, DS18B20 Temp, SSD1306 OLED

from machine import ADC, Pin, I2C
import onewire, ds18x20
import ssd1306
import time


class ECGSensor:
    """AD8232 ECG sensor on ESP32 ADC pin."""

    def __init__(self, adc_pin: int = 34):
        self._adc = ADC(Pin(adc_pin))
        self._adc.atten(ADC.ATTN_11DB)   # 0-3.6 V range
        self._adc.width(ADC.WIDTH_12BIT)  # 12-bit resolution

    def read_raw(self) -> int:
        """Return raw 12-bit ADC value (0-4095)."""
        return self._adc.read()

    def read_mv(self) -> float:
        """Return voltage in millivolts."""
        return self.read_raw() * (3600 / 4095)


class PulseOximeter:
    """MAX30100 SpO2 / Heart-rate sensor over I2C."""

    MAX30100_ADDR = 0x57
    REG_MODE_CONFIG   = 0x06
    REG_SPO2_CONFIG   = 0x07
    REG_FIFO_DATA     = 0x05

    def __init__(self, sda_pin: int = 21, scl_pin: int = 22):
        self._i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400_000)
        self._init_sensor()

    def _init_sensor(self):
        # SpO2 mode, 100 Hz sample rate, 1600 us pulse width
        self._i2c.writeto_mem(self.MAX30100_ADDR, self.REG_MODE_CONFIG, bytes([0x03]))
        self._i2c.writeto_mem(self.MAX30100_ADDR, self.REG_SPO2_CONFIG, bytes([0x47]))

    def read(self) -> tuple:
        """Return (heart_rate_bpm, spo2_percent) as ints."""
        # Simplified FIFO read; production code would average multiple samples
        raw = self._i2c.readfrom_mem(self.MAX30100_ADDR, self.REG_FIFO_DATA, 4)
        ir  = (raw[0] << 8) | raw[1]
        red = (raw[2] << 8) | raw[3]
        # Basic ratio-based SpO2 estimate
        ratio = red / ir if ir > 0 else 1.0
        spo2  = max(0, min(100, int(110 - 25 * ratio)))
        hr    = max(40, min(200, int(60 + (ir - 2048) / 100)))
        return hr, spo2


class TempSensor:
    """DS18B20 OneWire temperature sensor."""

    def __init__(self, data_pin: int = 4):
        ow  = onewire.OneWire(Pin(data_pin))
        self._ds = ds18x20.DS18X20(ow)
        self._roms = self._ds.scan()
        if not self._roms:
            raise RuntimeError("No DS18B20 found on pin %d" % data_pin)

    def read_celsius(self) -> float:
        """Trigger conversion and return temperature in Celsius."""
        self._ds.convert_temp()
        time.sleep_ms(750)  # max conversion time
        return round(self._ds.read_temp(self._roms[0]), 2)


class OLEDDisplay:
    """SSD1306 128x64 I2C OLED display."""

    def __init__(self, sda_pin: int = 21, scl_pin: int = 22, width: int = 128, height: int = 64):
        i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400_000)
        self._oled = ssd1306.SSD1306_I2C(width, height, i2c)

    def show(self, hr: int, spo2: float, temp: float):
        """Render vitals on OLED."""
        self._oled.fill(0)
        self._oled.text("IoT Health Monitor", 0, 0)
        self._oled.text(f"HR   : {hr} bpm", 0, 20)
        self._oled.text(f"SpO2 : {spo2}%", 0, 32)
        self._oled.text(f"Temp : {temp}C", 0, 44)
        self._oled.show()
