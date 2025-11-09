from machine import Pin, I2C
import network
import time
from utils.sensors import SCD40Sensor


# ---- Disable Wi-Fi ----
wlan = network.WLAN(network.STA_IF)
wlan.active(False)

# ---- Setup shared I2C instance ----
i2c = I2C(0, scl=Pin(7), sda=Pin(10), freq=400000)

sampling_timer = 10000

# ---- Main Data Recording Loop ----
def record_data(channel_maps, i2c):
    
    data_buffer = []  # Buffer to store sensor data before logging
    last_write_time = time.ticks_ms()  # Track the last time data was written to the SD card

    while True:
        current_time = time.ticks_ms()

        elapsed = time.ticks_diff(current_time, last_write_time)

        if elapsed >= sampling_timer:
            time.sleep_ms(50)
            sensor = SCD40Sensor(i2c)
            data = sensor.read_sensor()
            print(f"Data from {sensor_type}: {data}")
            last_write_time = time.ticks_ms()

        time.sleep_ms(50)  # Yield to CPU to prevent blocking

# ---- Start the process ----
record_data(channel_maps, i2c)