# PC-side tools for data_sensor_collector

This folder contains tools that run on a host computer (PC) and interact with the ESP32-C6 device-side firmware.

Purpose
- Receive sensor data over Bluetooth Low Energy (BLE) from one or more ESP32 devices and persist it to disk.
- Upload scripts and firmware to the ESP32 board from the host.

Contents
- `central_receiver.py` — BLE central that connects to target ESP32 peripherals, receives JSON-encoded batches of sensor readings, and appends them to a CSV file.
- `uploader.py` — Utility that locates the ESP32 serial port and uses `mpremote` / `esptool` to upload Python scripts or re-flash MicroPython firmware.
- `readme.md` — short note about the MicroPython firmware used for the board (kept here for reference).

## Project overview

The PC-side scripts complement the board-side firmware in `board/`:

- The board advertises as a BLE peripheral (see `board/utils/ble_sender.py`) and sends sensor data in small JSON batches using a custom characteristic.
- The PC-side `central_receiver.py` acts as a BLE central, subscribes to the characteristic, decodes the JSON batches and writes rows into a CSV file for later analysis.
- `uploader.py` is a convenience tool to copy Python files to the ESP32 filesystem with `mpremote` and to re-flash MicroPython using `esptool`.

This split keeps data acquisition on the embedded device and persistence/analysis on a more powerful host machine.

## Components

1) Central Receiver (`central_receiver.py`)

- Scans for BLE devices with names listed in `TARGET_NAMES` (default: `ESP32-SensorData-1`, `ESP32-SensorData-2`).
- Connects to each device and subscribes to a characteristic UUID (default: `6e400003-b5a3-f393-e0a9-e50e24dcca9e`).
- Each notification contains a UTF-8 JSON-encoded batch (list) of sensor reading dictionaries. The script parses the batch and appends the entries to a CSV file.
- By default the CSV output path is set in the `OUTPUT_FILE` variable inside the script — update it to a path appropriate for your OS.

CSV columns written (header produced on first run):

- Receiving_time — the host-side timestamp when the batch was processed
- Device_name — BLE device advertising name
- Time (s) — sensor timestamp value (if present in batch entries)
- Channel — multiplexer channel number
- Sensor_type — sensor label (e.g., "CO2" or "O2")
- CO2 (ppm), Temperature (°C), Humidity (%), O2 (%) — sensor result fields (empty if not applicable for the row)

2) Uploader (`uploader.py`)

- Attempts to auto-detect the ESP32 serial port (by scanning serial port descriptions for USB/ESP32/CP210/CH340 substrings).
- Uses `mpremote` to copy `.py` files from a configured `source` folder to the board filesystem. By default it excludes `boot.py` but will prompt to upload `boot.py` optionally.
- Offers an option to re-flash MicroPython using `esptool` (invokes `mpremote bootloader`, `esptool erase_flash`, and `esptool write_flash` commands). Adjust the firmware filename in the script to the desired image.

## Requirements & dependencies

- Python 3.8+ on the host machine
- pip-installable Python packages:
  - bleak (BLE central library)
  - ujson (used to parse the JSON batches in the receiver)
  - pyserial (provides `serial.tools.list_ports` used by the uploader)

Install required packages with pip:

```bash
python -m pip install bleak ujson pyserial
```

Tools required on PATH (for uploading / flashing):

- mpremote (recommended for file transfers):
  - Install via pip: `python -m pip install mpremote`
- esptool (required if re-flashing firmware):
  - Install via pip: `python -m pip install esptool`

Notes:
- On Linux you may need additional permissions for BLE and serial access (see Troubleshooting).
- The PC-side receiver uses the Bleak library which supports Windows, macOS and Linux — BLE backends and permissions vary by OS.

## Usage

1) Run the BLE central (receive data)

- Edit `central_receiver.py` and set `OUTPUT_FILE` to a path where you want the CSV saved.
- Run the script:

```bash
python pc_side/central_receiver.py
```

- The script scans for devices in `TARGET_NAMES`. When it finds a device it connects and listens for notifications on the configured characteristic UUID. Received batches are appended to the CSV file.

2) Verify a BLE connection manually

- On Linux/macOS you can use `bluetoothctl` or the OS Bluetooth UI to inspect advertisements and device names.
- As a quick programmatic check, run a small Bleak scanner snippet (Python):

```python
from bleak import BleakScanner
import asyncio

async def scan():
    devices = await BleakScanner.discover(timeout=5)
    for d in devices:
        print(d)

asyncio.run(scan())
```

Look for device names like `ESP32-SensorData-1` (these names are set on the board in `board/master.py`).

3) Upload scripts / re-flash firmware

- Run the uploader script and follow prompts (it will try to auto-detect the ESP32 serial port):

```bash
python pc_side/uploader.py
```

- Choose `1` to upload scripts; choose `2` to re-flash the MicroPython firmware (uploader will call `esptool`).
- Ensure `mpremote` and `esptool` are installed and available on your PATH.
- To work with the Python script of this repo on the ESP32-C6 board, it is necessary to download the proper firmware.
For this specific case, the scripts were tested with a Micropython firmware (v1.25.0 (2025-04-15).bin) retrieved from:

https://micropython.org/download/ESP32_GENERIC_C6/

If you prefer to copy files yourself, you can also use `mpremote` directly, for example:

```bash
mpremote connect auto fs cp board/master.py :
mpremote connect auto fs cp board/utils/sensors.py :
```

And to re-flash manually:

```bash
mpremote bootloader
esptool --chip esp32c6 --port /dev/ttyUSB0 erase_flash
esptool --chip esp32c6 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x0 path/to/firmware.bin
```

## File output description

- CSV output: `central_receiver.py` appends rows to the single CSV file defined by `OUTPUT_FILE`. Each notification batch can contain multiple sensor entries; each entry becomes one CSV row.
- JSON payload: The board sends JSON-encoded batches over BLE (the receiver parses these using `ujson.loads`). The receiver does not currently write a separate full JSON file — only the parsed rows are appended to CSV.

Example of a batch received over BLE (on the board side):

```json
[
  {"timestamp": 169..., "channel": 1, "sensor_type": "CO2", "data": [410, 24.1, 48.2]},
  {"timestamp": 169..., "channel": 0, "sensor_type": "O2", "data": 20.8}
]
```

The receiver will parse the above and write two rows to CSV.

## Integration notes

- BLE UUIDs and device names:
  - `central_receiver.py` expects notifications on characteristic UUID `6e400003-b5a3-f393-e0a9-e50e24dcca9e` — this matches the UUID used in `board/utils/ble_sender.py`.
  - The receiver looks for devices named in `TARGET_NAMES`; these names are set in `board/master.py` when creating the `BLEPeripheral` instance (e.g., `ESP32-SensorData-1`). Make sure board names match the list or update `TARGET_NAMES` on the PC side.

- Data format:
  - The board sends lists of dictionaries (JSON). Each dictionary should contain keys like `timestamp`, `channel`, `sensor_type` and `data`. The PC-side parser consumes this format directly.

## Troubleshooting

BLE issues
- No devices found when scanning:
  - Ensure the ESP32 is powered and `BLEPeripheral.advertise()` is running on the board.
  - Verify the board's BLE name by checking `board/master.py` and `board/utils/ble_sender.py`.
  - On Linux, ensure your user has permission to use Bluetooth or run the script with sudo for quick tests (prefer configuring capabilities instead of running as root).

- Connection drops or notifications not received:
  - BLE is sensitive to distance and RF environment. Move the devices closer and disable interfering radios.
  - Check prints on the board REPL (connect via serial) to see if `BLEPeripheral` reports connections/disconnections.

Uploader / serial issues
- `uploader.py` cannot find the ESP32 port:
  - Install the CP210x/CH340 drivers if needed (Windows) or check dmesg (Linux) after plugging the device in.
  - Run `python -m serial.tools.list_ports` to list available ports and identify the correct device.

- `mpremote` or `esptool` not found:
  - Install them with pip and ensure the Python scripts directory is on your PATH (or run them via `python -m mpremote`).

Permissions on Linux
- BLE scanning and connecting on Linux sometimes requires special access. Give your user access to Bluetooth or run tests with:

```bash
sudo setcap 'cap_net_raw+eip' $(which python3)
```

Or use appropriate system configuration for BlueZ access.

If you hit errors, capture the exception text from the PC script and the board REPL logs — they will help pinpoint whether the failure is BLE (advertise/connect/notify) or parsing/logging related.

## Extending the PC-side tools

- Write a small JSON dumper: save raw JSON payloads to a timestamped `.jsonl` file before parsing for CSV (helpful for debugging).
- Add per-device folders and separate CSV files if aggregating many boards.
- Create a small web dashboard or Grafana ingestion pipeline that tail-follows the CSV or JSONL files for live visualization.

## Example command lines

Run the receiver (from repo root):

```bash
python pc_side/central_receiver.py
```

Upload scripts or flash firmware:

```bash
python pc_side/uploader.py
```

Install dependencies:

```bash
python -m pip install bleak ujson pyserial mpremote esptool
```
