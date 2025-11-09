# pc_ble_receiver.py
import asyncio
import csv
from bleak import BleakScanner, BleakClient
from datetime import datetime
import ujson

TARGET_NAMES = ["ESP32-SensorData-1", "ESP32-SensorData-2"]
CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
OUTPUT_FILE = "C:\\Users\\Marco\\sensor_output.csv"  # Set your path here

def write_to_file(device_name, data):
    """
    Writes sensor data received from a BLE device to a CSV file.

    Args:
        device_name (str): The name of the BLE device sending the data.
        data (str): The JSON-encoded batch of sensor data received from the device.
    """
    file_exists = False
    try:
        with open(OUTPUT_FILE, "r") as f:
            file_exists = True
    except FileNotFoundError:
        pass

    with open(OUTPUT_FILE, "a", newline='') as f:
        writer = csv.writer(f)

        if not file_exists:
            # Write a header including all possible sensor data fields
            writer.writerow([
                "Receving_time", "Device_name", "Time (s)", "Channel", "Sensor_type",
                "CO2 (ppm)", "Temperature (°C)", "Humidity (%)", "O2 (%)"
            ])

        # Parse the batch JSON
        batch = ujson.loads(data)

        for entry in batch:
            reading_output = entry.get("data")
            print(type(reading_output))
            oxygen_output, co2, temperature, humidity = ["", "", "", ""]
            if isinstance(reading_output, (list, tuple)):
                if len(reading_output) == 3:
                    co2, temperature, humidity = reading_output
            elif isinstance(reading_output, (float, int)):
                oxygen_output = reading_output

            writer.writerow([
                datetime.now().isoformat(),    # Batch receive time
                device_name,
                entry.get("timestamp", ""),    # Sensor timestamp
                entry.get("channel", ""),
                entry.get("sensor_type", ""),
                co2,    # <- Fill if exists, else empty
                temperature,
                humidity,
                oxygen_output
            ])

    print(f"Logged to CSV from {device_name}: {data}")


async def connect_and_listen(device, device_name):
    """
    Connects to a BLE device and listens for notifications on a specific characteristic.

    Args:
        device (BleakDevice): The BLE device to connect to.
        device_name (str): The name of the BLE device.
    """
    try:
        async with BleakClient(device) as client:
            print(f"Connected to {device_name}")

            async def handle_notify(sender, data):
                """
                Handles notifications received from the BLE device.

                Args:
                    sender (int): The handle of the characteristic that sent the notification.
                    data (bytes): The data received from the notification.
                """
                decoded = data.decode("utf-8")
                write_to_file(device_name, decoded)

            await client.start_notify(CHAR_UUID, handle_notify)

            while client.is_connected:
                await asyncio.sleep(1)

            await client.stop_notify(CHAR_UUID)

    except Exception as e:
        print(f"Error with {device_name}: {e}")


async def find_device(target_name):
    """
    Scans for a BLE device with the specified name.

    Args:
        target_name (str): The name of the BLE device to search for.

    Returns:
        BleakDevice or None: The found BLE device, or None if not found.
    """
    print(f"Scanning for {target_name}...")
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name == target_name:
            print(f"Found {target_name}!")
            return d
    print(f"{target_name} not found.")
    return None


async def main():
    """
    Main function to manage the BLE scanning, connecting, and data logging process.

    Continuously cycles through the target BLE devices, attempting to connect and
    log data from each device in the `TARGET_NAMES` list.
    """
    current_idx = 0

    while True:
        target_name = TARGET_NAMES[current_idx]

        device = await find_device(target_name)

        if device:
            await connect_and_listen(device, target_name)
        else:
            print(f"Will retry {target_name} in next cycle.")

        # Move to next target device
        current_idx = (current_idx + 1) % len(TARGET_NAMES)

        # Small wait before trying next device
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
