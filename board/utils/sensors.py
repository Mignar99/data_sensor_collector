import time
from machine import I2C, Pin
import asyncio

'''
Based on Adafruit_CircuitPython_SCD4X repo on GitHub
'''
SCD40_ADDRESS = 0x62

class SCD40Sensor:
    """
    A class to interface with the SCD40 CO2 sensor using I2C communication.

    Attributes:
        i2c (I2C): The I2C interface used to communicate with the sensor.
    """

    def __init__(self, i2c):
        """
        Initializes the SCD40Sensor object and starts periodic measurement.

        Args:
            i2c (I2C): The I2C interface used to communicate with the sensor.
        """
        self.i2c = i2c
        self.start_periodic_measurement()

    def start_periodic_measurement(self):
        """
        Starts periodic measurement on the SCD40 sensor.
        """
        try:
            self.i2c.writeto(SCD40_ADDRESS, b'\x21\xb1')  # Start measurement
            print("Started periodic measurement.")
            time.sleep(2)  # Give it time to warm up
        except OSError as e:
            if e.args[0] == 19:  # ENODEV: Device probably already running
                started = True
            else:
                print("Failed to start measurement:", e)

    def crc8(self, data):
        """
        Computes the CRC8 checksum for the given data.

        Args:
            data (bytes): The data to compute the CRC for.

        Returns:
            int: The computed CRC8 checksum.
        """
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc

    def read_sensor(self):
        """
        Reads CO2, temperature, and humidity data from the SCD40 sensor.

        Returns:
            tuple: A tuple containing CO2 concentration (ppm), temperature (°C), and relative humidity (%).
        """
        try:
            self.i2c.writeto(SCD40_ADDRESS, b'\xEC\x05')
            time.sleep(1)
            data = self.i2c.readfrom(SCD40_ADDRESS, 9)

            def parse_word(start_index):
                raw = data[start_index:start_index+2]
                crc_received = data[start_index+2]
                if self.crc8(raw) != crc_received:
                    raise ValueError("CRC mismatch")
                return (raw[0] << 8) | raw[1]

            co2 = parse_word(0)
            temp_raw = parse_word(3)
            rh_raw = parse_word(6)

            temp = -45 + 175 * (temp_raw / 65535)
            humidity = 100 * (rh_raw / 65535)

            return co2, round(temp, 2), round(humidity, 2)

        except Exception as e:
            print("Sensor read error:", e)
            return None, None, None

'''
Based on DFRobot_OxygenSensor repo in GitHubs
'''
ADDRESS_0 = 0x70
ADDRESS_1 = 0x71
ADDRESS_2 = 0x72
ADDRESS_3 = 0x73

OXYGEN_DATA_REGISTER = 0x03
USER_SET_REGISTER = 0x08
AUTUAL_SET_REGISTER = 0x09
GET_KEY_REGISTER = 0x0A

MAX_BUFFER_SIZE = 101
EPSILON = 1e-6
DEFAULT_COLLECT_NUM = 10

class GravitySensor:
    """
    A class to interface with a Gravity oxygen sensor using I2C communication.

    Attributes:
        i2cbus (I2C): The I2C interface used to communicate with the sensor.
        _addr (int): The I2C address of the sensor.
        _key (float): Calibration key for oxygen data.
        _count (int): Number of data points collected.
        _txbuf (list): Buffer for transmitting data to the sensor.
        _oxygendata (list): Buffer for storing oxygen data.
        _init_success (bool): Indicates if the sensor was successfully initialized.
    """

    def __init__(self, i2c: I2C, addr: int = ADDRESS_3):
        """
        Initializes the GravitySensor object and attempts to initialize the sensor.

        Args:
            i2c (I2C): The I2C interface used to communicate with the sensor.
            addr (int): The I2C address of the sensor.
        """
        self.i2cbus = i2c
        self._addr = addr
        self._key = 20.9 / 120.0
        self._count = 0
        self._txbuf = [0]
        self._oxygendata = [0.0] * MAX_BUFFER_SIZE
        self._init_success = self._try_initialize()

    def _try_initialize(self) -> bool:
        """
        Attempts to initialize the sensor by reading a register.

        Returns:
            bool: True if initialization is successful, False otherwise.
        """
        try:
            self.read_reg(OXYGEN_DATA_REGISTER, 1)
            self.get_flash()
            return True
        except Exception as e:
            print("GravitySensor init failed:", e)
            return False

    def read_sensor(self, collect_num: int = DEFAULT_COLLECT_NUM) -> float:
        """
        Reads oxygen concentration data from the sensor.

        Args:
            collect_num (int): Number of data points to collect for averaging.

        Returns:
            float: The averaged oxygen concentration.
        """
        if not self._init_success:
            return -1.0
        return round(self.get_oxygen_data(collect_num), 2)

    def get_flash(self):
        """
        Reads the calibration key from the sensor's flash memory.
        """
        result = self.read_reg(GET_KEY_REGISTER, 1)
        value = result[0]
        self._key = 20.9 / 120.0 if value == 0 else float(value) / 1000.0
        time.sleep(0.1)

    def calibrate(self, vol: float, mv: float):
        """
        Calibrates the sensor with a given volume and millivolt value.

        Args:
            vol (float): Volume of oxygen.
            mv (float): Millivolt value for calibration.
        """
        if abs(mv) < EPSILON:
            self._txbuf[0] = int(vol * 10)
            self.write_reg(USER_SET_REGISTER, self._txbuf)
        else:
            self._txbuf[0] = int((vol / mv) * 1000)
            self.write_reg(AUTUAL_SET_REGISTER, self._txbuf)

    def get_oxygen_data(self, collect_num: int) -> float:
        """
        Collects and averages oxygen data from the sensor.

        Args:
            collect_num (int): Number of data points to collect for averaging.

        Returns:
            float: The averaged oxygen concentration.
        """
        if collect_num <= 0 or collect_num > MAX_BUFFER_SIZE:
            return -1.0

        self.get_flash()

        for i in range(collect_num - 1, 0, -1):
            self._oxygendata[i] = self._oxygendata[i - 1]

        result = self.read_reg(OXYGEN_DATA_REGISTER, 3)
        val = self._key * (result[0] + result[1] / 10.0 + result[2] / 100.0)
        self._oxygendata[0] = val

        self._count = min(self._count + 1, collect_num)
        return self._average(self._oxygendata, self._count)

    def _average(self, array, length):
        """
        Computes the average of the given array.

        Args:
            array (list): The array of values.
            length (int): The number of values to average.

        Returns:
            float: The computed average.
        """
        return sum(array[:length]) / float(length)

    def write_reg(self, reg: int, data: list):
        """
        Writes data to a specific register on the sensor.

        Args:
            reg (int): The register address.
            data (list): The data to write.

        Raises:
            OSError: If the I2C write operation fails.
        """
        try:
            self.i2cbus.writeto(self._addr, bytes([reg] + data))
        except Exception as e:
            raise OSError("I2C write failed: {}".format(e))

    def read_reg(self, reg: int, length: int) -> list:
        """
        Reads data from a specific register on the sensor.

        Args:
            reg (int): The register address.
            length (int): The number of bytes to read.

        Returns:
            list: The data read from the register.

        Raises:
            OSError: If the I2C read operation fails.
        """
        try:
            self.i2cbus.writeto(self._addr, bytes([reg]))
            data = self.i2cbus.readfrom(self._addr, length)
            return list(data)
        except Exception as e:
            raise OSError("I2C read failed: {}".format(e))
