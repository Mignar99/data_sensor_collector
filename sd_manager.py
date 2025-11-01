import time
import machine
import os
import sdcard

class SDCardLogger:
    """
    A class to manage logging data to an SD card using SPI communication.

    Attributes:
        cs_pin (int): Chip select pin for the SD card.
        timer (float): Timer interval in seconds for logging.
        device_name (str): Name of the device for logging purposes.
        log_file (str): Path to the log file on the SD card.
        data_buffer (list): Buffer to temporarily store data before logging.
        spi (machine.SPI): SPI interface for SD card communication.
        cs (machine.Pin): Chip select pin object.
    """

    def __init__(self, cs_pin=20, timer=30000, device_name=None, log_file='/sd/log_sensors.txt'):
        """
        Initializes the SDCardLogger object and sets up the SD card.

        Args:
            cs_pin (int): Chip select pin for the SD card.
            timer (int): Timer interval in milliseconds for logging.
            device_name (str): Name of the device for logging purposes.
            log_file (str): Path to the log file on the SD card.
        """
        self.data_buffer = []
        self.device_name = device_name
        self.timer = timer / 1000
        self.cs_pin = cs_pin
        self.log_file = log_file

        # Set up SPI for SD card
        self.spi = machine.SPI(1, baudrate=1000000, sck=machine.Pin(6), mosi=machine.Pin(19), miso=machine.Pin(18))
        self.cs = machine.Pin(self.cs_pin, machine.Pin.OUT)

        # Mount the SD card once at the start
        self._mount_sd()

    def _mount_sd(self):
        """
        Mounts the SD card if not already mounted.

        Returns:
            bool: True if the SD card is successfully mounted, False otherwise.
        """
        try:
            sd = sdcard.SDCard(self.spi, self.cs)

            if not os.statvfs("/sd"):  # Check if SD card is mounted
                vfs = os.VfsFat(sd)
                os.mount(vfs, "/sd")  # Mount the SD card to /sd
                print("SD card mounted successfully.")
            else:
                print("SD card already mounted.")
        except Exception as e:
            print("Failed to mount SD card:", e)
            return False

        # Verify if the directory exists after mounting
        if '/sd' not in os.listdir('/'):
            try:
                vfs = os.VfsFat(sd)
                os.mount(vfs, "/sd")  # Mount the SD card to /sd
                print("Created /sd directory.")
            except Exception as e:
                print("Failed to create /sd directory: ALREADY EXISTS")
                return False

        return True

    def _prepare_log_file(self):
        """
        Ensures the log file exists and contains headers.
        """
        try:
            print("Listing /sd directory:", os.listdir('/sd'))  # Check contents of /sd

            if self.log_file.split('/')[-1] not in os.listdir('/sd'):
                with open(self.log_file, 'w') as f:
                    header = 'timestamp,channel_id,sensor_type,data\n'
                    f.write(header)
                print("Log file created with headers.")
            else:
                print("Log file already exists.")
        except Exception as e:
            print("Failed to create or check log file:", e)

    def _format_data(self, data):
        """
        Formats the data for CSV (handles list of values).

        Args:
            data (list or any): Data to format.

        Returns:
            str: Formatted data as a string.
        """
        if isinstance(data, list):
            return ','.join(map(str, data))
        return str(data)

    def log_data(self, data_buffer):
        """
        Logs the collected data to the SD card in CSV format.

        Args:
            data_buffer (list): List of data entries to log.
        """
        self.data_buffer.append(data_buffer)
        try:
            if os.statvfs("/sd"):
                print('The SD card is correctly mounted')
            self._prepare_log_file()

            with open(self.log_file, 'a') as f:
                for entry in data_buffer:
                    timestamp_str = str(int(entry["timestamp"] / self.timer))
                    data_str = self._format_data(entry["data"])
                    line = f"{timestamp_str},{self.device_name},{entry['channel']},{entry['sensor_type']},{data_str}\n"

                    f.write(line)

            print("Data logged successfully.")
        except Exception as e:
            print("Failed to log to SD card:", e)

    def read_sd_file(self, file_path='/sd/sensor_output.txt'):
        """
        Reads the contents of a file on the SD card and sends it over serial.

        Args:
            file_path (str): Path to the file to read.
        """
        try:
            with open(file_path, 'r') as f:
                data = f.read()
                print("Sending file content over serial...")
                # Send the file content over serial to the PC
                print(data)
        except Exception as e:
            print("Error reading SD card file:", e)

    def clear_buffer(self):
        """
        Clears the data buffer after logging.
        """
        self.data_buffer.clear()
        print("Buffer cleared.")
