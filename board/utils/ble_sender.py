import bluetooth
import machine
import time
import master
import ujson

"""
This script defines the BLEPeripheral class, which manages Bluetooth Low Energy (BLE) communication
for an ESP32 device. It allows the device to advertise itself, establish connections with a central device,
and send data in batches over a custom BLE service and characteristic.

The BLEPeripheral class is designed to:
- Advertise the device with a custom name.
- Handle connection and disconnection events.
- Send sensor data in batches to a connected central device.
- Buffer data when not connected and retry sending when reconnected.
"""

class BLEPeripheral:
    """
    A class to manage Bluetooth Low Energy (BLE) communication for an ESP32 device.

    Attributes:
        name (str): The name of the BLE device.
        buffer (list): A buffer to store data when the device is not connected.
        ble (bluetooth.BLE): The BLE instance for managing BLE operations.
        conn_handle (int): The connection handle for the central device.
        SERVICE_UUID (bluetooth.UUID): The UUID for the custom BLE service.
        CHAR_UUID (bluetooth.UUID): The UUID for the custom BLE characteristic.
        CHAR (tuple): The characteristic definition (UUID and properties).
        SERVICE (tuple): The service definition (UUID and characteristics).
        tx_handle (int): The handle for the characteristic used for data transmission.
    """

    def __init__(self, name="ESP32-Random"):
        """
        Initializes the BLEPeripheral object, sets up the BLE service and characteristic,
        and starts advertising.

        Args:
            name (str): The name of the BLE device (default is "ESP32-Random").
        """
        self.name = name
        self.buffer = []
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        
        self.conn_handle = None

        # Define custom service and characteristic UUIDs
        self.SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        self.CHAR_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

        self.CHAR = (self.CHAR_UUID, bluetooth.FLAG_NOTIFY | bluetooth.FLAG_READ)
        self.SERVICE = (self.SERVICE_UUID, (self.CHAR,))
        ((self.tx_handle,),) = self.ble.gatts_register_services((self.SERVICE,))
        self.ble.irq(self.bt_irq)
        self.advertise()

    def advertise(self):
        """
        Starts advertising the BLE device with the specified name.
        """
        name = bytes(self.name, 'utf-8')
        adv_data = bytearray('\x02\x01\x06', 'utf-8') + bytearray((len(name) + 1, 0x09)) + name
        self.ble.gap_advertise(100_000, adv_data)
        print("Advertising as:", self.name)

    def bt_irq(self, event, data):
        """
        Handles BLE events such as connection and disconnection.

        Args:
            event (int): The BLE event type (e.g., connection or disconnection).
            data (tuple): Additional data associated with the event.
        """
        if event == 1:  # Central connected
            self.conn_handle, address_type, address = data
            print("Connected")
        elif event == 2:  # Central disconnected
            self.conn_handle = None
            print("Disconnected")

    def send_data(self, data):
        """
        Sends data over BLE. Buffers the data if not connected and retries when reconnected.

        Args:
            data (list): A list of data entries to send.
        """
        if self.conn_handle is None:
            print("Not connected, buffering data.")
            for d in data:
                self.buffer.append(d)
            self.enable_ble()
            return
        # If connected, prepare data to send
        try:
            # Always send buffered data first
            for d in data:
                self.buffer.append(d)
            all_data = self.buffer
            # Group the data into batches of 2-5 dictionaries for efficient transfer 
            BATCH_SIZE = 2  # Adjust for optimal performance depending on the size
            for i in range(0, len(all_data), BATCH_SIZE):
                batch = all_data[i:i + BATCH_SIZE]
                batch_str = ujson.dumps(batch)
                batch_bytes = batch_str.encode("utf-8")
                
                print(f"Sending batch of {len(batch)} items...")  # Debugging line
                
                # Write the data to the characteristic
                self.ble.gatts_write(self.tx_handle, batch_bytes)
                self.ble.gatts_notify(self.conn_handle, self.tx_handle, batch_bytes)
                
                time.sleep_ms(20)  # Small delay between sending each batch to ensure stability
                
            # Clear the buffer after successful send
            print("Data sent successfully.")
            self.buffer.clear()
            self.shutdown_ble()
        
        except Exception as e:
            print("Error sending data, buffering...", e)
            # Re-buffer data if send fails
            for d in data:
                self.buffer.append(d)

    def shutdown_ble(self):
        """
        Disables the BLE module to save power.
        """
        print("Disabling Bluetooth...")
        self.ble.active(False)

    def enable_ble(self):
        """
        Enables the BLE module and restarts advertising.
        """
        print("Enabling Bluetooth...")
        self.ble.active(True)
        self.conn_handle = None
        self.ble.irq(self.bt_irq)
        self.tx_handle = self.ble.gatts_register_services((self.SERVICE,))[0][0]
        self.advertise()

