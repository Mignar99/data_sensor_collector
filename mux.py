from machine import Pin
import time

class Multiplexer:
    """
    A class to control a multiplexer using GPIO pins.

    Attributes:
        name (str): The name of the multiplexer.
        en (Pin): The enable pin for the multiplexer.
        control_pins (list): A list of GPIO pins used to control the multiplexer channels.
        i2c: The I2C interface (not used in this implementation).
    """

    def __init__(self, name, s_pins, en_pin, i2c):
        """
        Initializes the Multiplexer object.

        Args:
            name (str): The name of the multiplexer.
            s_pins (list): A list of GPIO pin numbers for channel selection.
            en_pin (int): The GPIO pin number for the enable pin.
            i2c: The I2C interface (not used in this implementation).
        """
        self.name = name
        self.en = Pin(en_pin, Pin.OUT)
        self.en.value(0)

        self.control_pins = [Pin(pin, Pin.OUT) for pin in s_pins]
        self.i2c = i2c
        self.disable()

    def select_channel(self, channel):
        """
        Selects a specific channel on the multiplexer.

        Args:
            channel (int): The channel number to select (0-15).

        Raises:
            ValueError: If the channel is not between 0 and 15.
        """
        if not 0 <= channel <= 15:
            raise ValueError("Channel must be between 0 and 15")
        
        self.enable()
        bits = [int(b) for b in "{:04b}".format(channel)]
        for pin, val in zip(self.control_pins, bits):
            pin.value(val)
        time.sleep_ms(10)

    def disable(self):
        """
        Disables the multiplexer by setting the enable pin to high.
        """
        self.en.value(1)

    def enable(self):
        """
        Enables the multiplexer by setting the enable pin to low.
        """
        self.en.value(0)
