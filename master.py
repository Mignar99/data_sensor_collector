from machine import Pin, I2C
import network
import time
from utils.mux import Multiplexer
from utils.sensors import SCD40Sensor, GravitySensor
from utils.sd_manager import SDCardLogger  # Import the SDLogger class
from utils.ble_sender import BLEPeripheral

"""
This script manages the data collection process from multiple sensors connected via a multiplexer (MUX),
logs the data to an SD card, and sends the data via BLE (Bluetooth Low Energy).

It uses the following components:
- Multiplexer: To switch between multiple sensor channels.
- Sensors: SCD40Sensor (CO2, temperature, humidity) and GravitySensor (oxygen concentration).
- SDCardLogger: To log sensor data to an SD card.
- BLEPeripheral: To send sensor data to a BLE receiver.

The script operates in a loop, periodically reading data from sensors, logging it to the SD card,
and transmitting it via BLE.
"""

# ---- Disable Wi-Fi ----
wlan = network.WLAN(network.STA_IF)
wlan.active(False)

# ---- Setup shared I2C instance ----
i2c_mux1 = I2C(0, scl=Pin(7), sda=Pin(10), freq=400000)

# ---- Setup Multiplexers ----
mux = Multiplexer("MUX1", s_pins=[5, 4, 3, 2], en_pin=11, i2c=i2c_mux1)

# ---- Channel Map with Alternating Sensors ----
channel_maps = {
    0: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()},  # Channel 0 -> GravitySensor
    1: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 1 -> SCD40Sensor
    2: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()},  # Channel 2 -> GravitySensor
    3: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 3 -> SCD40Sensor
    4: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()},  # Channel 4 -> GravitySensor
    5: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 5 -> SCD40Sensor
    6: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()},  # Channel 6 -> GravitySensor
    7: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 7 -> SCD40Sensor
    8: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()},  # Channel 8 -> GravitySensor
    9: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 9 -> SCD40Sensor
    10: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()}, # Channel 10 -> GravitySensor
    11: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 11 -> SCD40Sensor
    12: {'sensor_type': "GravitySensor", 'interval': 15000, 'last': time.ticks_ms()},  # Channel 12 -> GravitySensor
    13: {'sensor_type': "SCD40Sensor", 'interval': 5000, 'last': time.ticks_ms()}, # Channel 13 -> SCD40Sensor
}
sampling_timer = 30000

# ---- Initialize SDLogger ----
name = "ESP32-SensorData-1"
sd_logger = SDCardLogger(cs_pin=20, device_name=name, timer=sampling_timer)

# ---- Initialize BLEPeripheral ----
ble_peripheral = BLEPeripheral(name=name)

# ---- Main Data Recording Loop ----
def record_data(channel_maps, i2c, sd_logger):
    """
    Main data recording loop that collects sensor data, logs it to the SD card, and sends it via BLE.

    Args:
        channel_maps (dict): A dictionary mapping MUX channels to sensor configurations.
        i2c (I2C): The shared I2C instance used for communication with sensors.
        sd_logger (SDCardLogger): The SDCardLogger instance for logging data to the SD card.
    """
    data_buffer = []  # Buffer to store sensor data before logging
    last_write_time = time.ticks_ms()  # Track the last time data was written to the SD card

    while True:
        current_time = time.ticks_ms()

        # Collect sensor data from the multiplexer channels
        for channel, info in channel_maps.items():
            elapsed = time.ticks_diff(current_time, info["last"])

            # Check if it's time to read this sensor based on its interval
            if elapsed >= sampling_timer:
                if channel == 0:
                    print(f"Reading at {current_time // 1000}s")

                mux.select_channel(channel)
                time.sleep_ms(100)
                sensor_type = info["sensor_type"]
                info["last"] = current_time  # Update the last read time for this sensor

                # Initialize the appropriate sensor class based on the channel
                if sensor_type == "SCD40Sensor":
                    sensor = SCD40Sensor(i2c)
                    sensor_label = "CO2"
                elif sensor_type == "GravitySensor":
                    sensor = GravitySensor(i2c)
                    sensor_label = "O2"

                # Read the sensor data
                data = sensor.read_sensor()
                print(f"Data from channel {channel} ({sensor_type}): {data}")

                # Append the data to the buffer
                data_buffer.append({
                    "timestamp": current_time / 1000,
                    "channel": channel,
                    "sensor_type": sensor_label,
                    "data": data
                })

        # Check if it's time to write to the SD card (every 60 seconds)
        if time.ticks_diff(current_time, last_write_time) >= 60000:  # 60 seconds
            sd_logger.log_data(data_buffer)  # Log the buffer to the SD card
            ble_peripheral.send_data(data_buffer)  # Send the data via BLE
            data_buffer.clear()  # Clear the buffer after writing
            last_write_time = current_time  # Reset the last write time

        time.sleep_ms(50)  # Yield to CPU to prevent blocking

# ---- Start the process ----
record_data(channel_maps, i2c_mux1, sd_logger)