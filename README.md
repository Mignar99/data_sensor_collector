# Data Sensor Collector — Overview

This repository contains firmware and host-side tools for collecting environmental sensor data with an ESP32-C6 device.

Please read the detailed documentation in the two subfolders:

- `board/README.md` — instructions and details for the ESP32-C6 firmware. It explains hardware wiring, MicroPython setup, the main acquisition loop (`master.py`), sensor drivers (SCD40 and Gravity O2), SD logging, and BLE peripheral behavior.
- `pc_side/README.md` — instructions and details for the PC-side tools. It explains how the BLE central (`central_receiver.py`) collects JSON batches from the board and writes CSV files, and how `uploader.py` can transfer scripts or re-flash MicroPython on the board.

## Quick summary

- What runs on the board (`board/`): the ESP32-C6 runs MicroPython code that reads an SCD40 CO₂ sensor and Gravity O₂ sensors (via an I2C multiplexer), buffers readings, writes logs to an SD card, and advertises/transmits batches over Bluetooth Low Energy using a custom characteristic.
- What runs on the host (`pc_side/`): a Python BLE central scans for ESP32 devices, connects, subscribes to notifications on a matching UUID, parses JSON batches and appends parsed rows to a CSV file for analysis. The PC-side also provides a helper to upload scripts and re-flash firmware.

## Why this setup is useful

This architecture is designed to deliver high-quality environmental data collection in places where space and hardware resources are limited. By using an I²C multiplexer, a single ESP32-C6 board can manage several gas sensors in parallel—CO₂, O₂, or additional sensors—without needing multiple boards. This reduces hardware cost, simplifies wiring, and keeps the footprint small.

Running several measurements at once makes it possible to track how atmospheric composition changes around a biological or chemical system in real time. These parallel readings help reveal correlations between gas dynamics and processes such as metabolic activity, growth phases, or reaction behavior.

The setup also supports both long-term logging and live monitoring: the board stores high-resolution data on an SD card while simultaneously streaming batches over BLE to a host computer. This combination allows teams to observe experiments as they unfold and still retain complete datasets for analysis later.

## Getting started

1. Read `board/README.md` for hardware wiring and how to flash MicroPython onto the ESP32-C6.
2. Read `pc_side/README.md` for instructions on installing Python dependencies (Bleak, pyserial, etc.), running the BLE receiver, and using the uploader.
