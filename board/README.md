## Project overview

This firmware runs on an ESP32-C6 and collects environmental data from two sensors:

- SCD40 — Sensirion CO₂, temperature and humidity sensor (I2C).
- GravitySensor — an I2C-based Oxygen sensor (DFRobot "Gravity" style I2C oxygen module).

The code in this directory is executed automatically at startup via `boot.py`. The main runtime is implemented in `master.py`, which reads sensors via an I2C multiplexer, logs data to an SD card, and transmits data over BLE.

## Hardware requirements

- ESP32-C6 development board (running MicroPython).
- Sensirion SCD40 CO₂ sensor (I2C)
- Gravity oxygen sensor (I2C; common "Gravity" oxygen sensor modules use addresses in 0x70–0x73)
- Optional: I2C multiplexer (the code expects an external multiplexer controlled via GPIO lines)
- SD card + SD card breakout (SPI/CS pin usage shown below)
- Wires, power supply

Recommended: power sensors at the voltage they expect (typically 3.3V or 5V depending on module); ensure common ground between modules and the ESP32.

### Wiring (as used in the code)

These wiring details reflect the pin assignments found in `master.py` and `board/examples/quick_test.py`.

- I2C bus (shared):
  - SCL -> GPIO 7
  - SDA -> GPIO 10
  - I2C frequency: 400 kHz

- Multiplexer control pins (for the configured multiplexer instance `Multiplexer("MUX1", s_pins=[5,4,3,2], en_pin=11, i2c=i2c_mux1)`):
  - S-pin bus -> GPIOs 5, 4, 3, 2 (select lines)
  - EN (enable) -> GPIO 11

- SD card chip-select (CS): GPIO 20 (used by `SDCardLogger` constructor in `master.py`)

Notes:
- The Gravity oxygen sensors in the project are addressed using I2C addresses 0x70–0x73 by default (constants in `board/utils/sensors.py`). The code instantiates `GravitySensor(i2c, addr=ADDRESS_3)` by default which maps to 0x73.
- The SCD40 default I2C address used in the driver is 0x62.

If your board or wiring differs, update `master.py` (the `I2C(...)` and `Multiplexer(...)` lines) or the wiring on the board to match.

## Software setup

1. Install MicroPython for ESP32-C6 on your board. Download the appropriate firmware from the official MicroPython downloads page and flash it to the board.

   Example (conceptual) steps:

   ```bash
   # Erase and flash (replace with the exact firmware file and device path)
   esptool.py --chip esp32c6 erase_flash
   esptool.py --chip esp32c6 write_flash -z 0x1000 firmware-esp32c6.bin
   ```

2. Copy the repository files to the board so `boot.py` and `master.py` are present in the device root. You can use `mpremote`, `ampy`, `rshell`, or other MicroPython file transfer tools.

   Example with mpremote:

   ```bash
   # Copy all files under board/ to the device filesystem
   mpremote connect /dev/ttyUSB0 fs put board/ :
   ```

3. Reboot the board. `boot.py` runs automatically at power-on and should start the main program (`master.py`).

Dependencies used in the codebase (MicroPython-friendly):

- Built-in `machine` module (I2C, Pin)
- `board/utils/sensors.py` contains simple MicroPython drivers for SCD40 and a Gravity oxygen sensor.

If you need a dependency not present in the base firmware, copy the module into the device filesystem.

## File structure (key files)

Files in `board/` you should know:

- `boot.py` — executed at startup. It ensures the device boots into the user program. (Note: this project includes `boot.py` to automatically trigger main behavior.)
- `master.py` — main application loop. Sets up I2C, the multiplexer, SD logger, BLE peripheral, and runs the data collection loop.
- `examples/quick_test.py` — small example that demonstrates reading the SCD40 sensor directly (useful for quick validation).
- `board/utils/sensors.py` — simple sensor drivers:
  - `SCD40Sensor` — I2C-based SCD40 driver; returns (CO2 ppm, temperature °C, relative humidity %).
  - `GravitySensor` — I2C-based oxygen sensor driver; returns oxygen concentration as a float.
- `utils/mux.py`, `utils/sd_manager.py`, `utils/ble_sender.py` — support modules used by `master.py` for multiplexer control, SD logging, and BLE communication respectively.

Wrap-up: `boot.py` starts the board and `master.py` runs the full acquisition pipeline.

## How it works

High-level flow (in `master.py`):

1. Disable Wi-Fi.
2. Create shared I2C instance: `I2C(0, scl=Pin(7), sda=Pin(10), freq=400000)`.
3. Initialize the multiplexer (`Multiplexer(...)`) that allows switching between many physical sensor channels.
4. Prepare `channel_maps` that map MUX channels (0..13) to sensor types. The code alternates Gravity and SCD40 sensors on channels.
5. Enter the main loop (`record_data`) which:
   - Iterates channels, selects the channel on the multiplexer, waits briefly, initializes the proper sensor object, and calls its `read_sensor()` method.
   - Appends the reading to an in-memory buffer.
   - Every 60 seconds, writes the buffer to the SD card via `SDCardLogger.log_data()` and sends the data via BLE using `BLEPeripheral.send_data()`.

Timing notes:
- `master.py` declares `sampling_timer = 30000` (30 seconds) and uses it to gate reads; individual channel entries also contain an `interval` value (5000ms for SCD40, 15000ms for Gravity) but the main loop currently checks against the global `sampling_timer`. This means the effective read cadence will follow `sampling_timer` unless you update the loop to use per-channel `interval` values.

Communication protocols used:

- I2C — SCD40 and GravitySensor use I2C (addresses in code: SCD40 = 0x62; Gravity default addresses 0x70-0x73).
- The multiplexer control lines are regular GPIO outputs (to select channels and enable/disable the MUX).
- SD card access is handled via the `SDCardLogger` (SPI/SD interface as configured in that module). The CS pin used in `master.py` is GPIO 20.
- BLE — data is sent via a simple BLE peripheral implemented in `utils/ble_sender.py`.

## Data output

What is collected:

- SCD40Sensor.read_sensor() -> (co2_ppm, temperature_c, humidity_pct)
- GravitySensor.read_sensor() -> oxygen_pct (float) or -1.0 if init fails

Where data goes:

- In-memory buffer in `master.py` while collecting.
- Periodically (every 60s by default), the buffer is written to the SD card using `SDCardLogger.log_data()` and transmitted using `BLEPeripheral.send_data()`.

Verifying data on the SD card:

- After a successful run, mount the SD card on a host machine and inspect the log files created by the `SDCardLogger`.

Directly viewing serial output:

- Connect to the board's REPL (e.g. `screen /dev/ttyUSB0 115200` or `mpremote connect /dev/ttyUSB0 repl`) and watch for print statements such as:
  - "Started periodic measurement." (SCD40 driver)
  - "Reading at ..." and "Data from channel X (SensorType): ..."

## Troubleshooting & testing

Common checks and fixes:

- No I2C devices found:
  - Verify wiring (SCL/SDA, VCC, GND).
  - Run a simple I2C scan in the REPL:

    ```python
    from machine import Pin, I2C
    i2c = I2C(0, scl=Pin(7), sda=Pin(10), freq=400000)
    print(i2c.scan())
    ```

  - Expected addresses: SCD40 -> 0x62 (shown in driver), Gravity sensors -> 0x70..0x73 depending on sensor.

- SCD40 "start measurement" error or CRC errors:
  - The SCD40 driver attempts to start periodic measurement; if the sensor is not powered or miswired you'll see I2C OSError messages or CRC mismatch messages. Confirm power and I2C pull-ups if needed.

- GravitySensor init failed:
  - The driver attempts to read registers at startup; if the wrong I2C address or wiring is used it will print an init failure. Try switching the `addr` argument when instantiating `GravitySensor(i2c, addr=0x70)` to match your module address.

- SD card logging issues:
  - Check that the SD card is inserted and the CS pin wiring matches the `SDCardLogger` constructor used in `master.py` (CS pin = 20 by default in the code).

Testing tips:

- Start with `examples/quick_test.py` to validate the SCD40 on the I2C bus (it builds a simple I2C instance and reads the SCD40).
- Use the REPL to manually create `SCD40Sensor(i2c)` and call `read_sensor()` to verify values before running full `master.py`.

## Notes & assumptions

- This README uses pin assignments and addresses found in the repository files (`master.py`, `board/examples/quick_test.py`, and `board/utils/sensors.py`). If you change wiring or pins, update those files accordingly.
- The repository owner is `Mignar99`; if you are the owner please add license info (LICENSE file) if required.

## License / Author

Author: Mignar99 (repository owner)

If a license file is present at the repository root, follow that license. If none is present and you plan to redistribute, add an appropriate `LICENSE` file (e.g., MIT) to the repo.

---

If you want, I can also:

- Add a short troubleshooting script (e.g., an `i2c_scan.py`) to the `board/examples/` folder for simple validation.
- Update `master.py` to honor the per-channel `interval` values instead of the global `sampling_timer` (makes sampling cadence configurable per sensor).

If you'd like either of those, tell me which and I'll make the change.
