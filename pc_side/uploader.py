import os
import subprocess

from serial.tools import list_ports

def find_esp32_port():
    """
    Finds the serial port to which the ESP32 board is connected.

    Returns:
        str: The device name of the ESP32 port (e.g., "COM5" or "/dev/ttyUSB0").
        None: If no ESP32 port is found.
    """
    ports = list_ports.comports()
    for port in ports:
        if "USB" in port.description or "ESP32" in port.description or "CP210" in port.description or "CH340" in port.description:
            return port.device
    return None

def upload_scripts():
    """
    Uploads Python scripts to the ESP32 board using the `mpremote` tool.

    This function scans the specified folder for `.py` files, excluding any files
    listed in the `ignore_files` list, and uploads them to the ESP32 board. It also
    provides an option to upload the `boot.py` file if desired by the user.

    Raises:
        FileNotFoundError: If the source folder or files are not found.
    """
    # Specify the files to ignore (these files will not be uploaded)
    ignore_files = ['boot.py']

    # Get all .py files in the folder
    files_to_upload = [
        f for f in os.listdir(source) if f.endswith('.py') and f not in ignore_files
    ]

    # Remove the existing boot.py file from the ESP32 board
    subprocess.run(['mpremote', 'connect', 'auto', 'fs', 'rm', "boot.py", ':'])

    # Iterate through the list of files and upload each one to the ESP32 board
    for file in files_to_upload:
        file_path = os.path.join(source, file)  # Construct the full path to the file
        subprocess.run(['mpremote', 'connect', 'auto', 'fs', 'cp', file_path, ':'])

    # Ask the user if they want to upload the boot.py file
    spec_boot = input('Would you also like to upload the boot.py file? [y/n]\n')
    if spec_boot == 'y':
        subprocess.run(['mpremote', 'connect', 'auto', 'fs', 'cp', os.path.join(source, 'boot.py'), ':'])

    print("Files uploaded successfully!")

"""
This script automates the process of uploading Python files to an ESP32 board using the `mpremote` tool.

The script scans a specified folder for `.py` files, excluding any files listed in the `ignore_files` list,
and uploads them to the ESP32 board via the `mpremote` tool. This is useful for deploying
multiple Python scripts to the ESP32 board in a single operation.
"""

# Specify the folder where your .py files are located
folder_path = os.path.abspath(os.path.dirname(__file__))
source_path = folder_path.split("\\")[:-1]
source = ("\\").join(source_path) + "\\molotov"
micropython_firmware = folder_path + '\\' + 'ESP32_GENERIC_C6-20250415-v1.25.0.bin'
current_port = find_esp32_port()

# Main script execution
desidered_process = input('Choose task to carry on:\n1. Upload files on board\n2. Re-flash Micropython\n')

if desidered_process == '1':
    """
    Option 1: Upload Python files to the ESP32 board.
    """
    upload_scripts()

if desidered_process == '2':
    """
    Option 2: Re-flash the ESP32 board with the specified MicroPython firmware.

    This process erases the flash memory of the ESP32 board and writes the new firmware.
    """
    subprocess.run(['mpremote', 'bootloader'])
    subprocess.run(['esptool', '--chip', 'esp32c6', '--port', current_port, 'erase_flash'])
    subprocess.run(['esptool', '--chip', 'esp32c6', '--port', current_port, '--baud', '460800', 'write_flash', '-z', '0x0', micropython_firmware])

