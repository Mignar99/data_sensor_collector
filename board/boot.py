# boot.py
import time
import machine
import os

# Wait a moment to allow the board to settle
time.sleep(1)

# You can also use exec if needed:
# exec(open("scd40_read.py").read())
import master
