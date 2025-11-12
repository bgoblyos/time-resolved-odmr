# Copyright (c) 2025 Bence Göblyös

import serial      # Serial communication
import time        # Timeout handling
import numpy as np # Math

"""
Kuhne MKU LO 8-13 PLL
"""
class KuhnePLL():
    def __init__(self, port, timeout = 1.0):
        self.device = None
        try:
            self.device = serial.Serial(
                port = port,
                baudrate = 115200,
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout = timeout,
            )
        except serial.SerialException as err:
            print(f"Failed to connect to oscillator with reason: {err}")

    def sendCommand(self, cmd, timeout = 1.0, capture_output = True):
        try:
            self.device.reset_input_buffer()
            nchar = self.device.write(cmd.encode())
            time.sleep(timeout)

            if capture_output:
                resp = self.device.read_all().decode().strip()
                return nchar, resp

            else:
                return nchar, None 

        except serial.SerialException as err:
            print(f"Sending command to oscillator failed with reason: {err}")
            return -1, err

    def setHZ(self, val):
        hz = str(round((np.floor(val) % 1000))).zfill(3)
        khz = str(round(np.floor(val*1e-3) % 1000)).zfill(3)
        mhz = str(round(np.floor(val*1e-6) % 1000)).zfill(3)
        ghz = str(round(np.floor(val*1e-9) % 1000)).zfill(3)

        
        for (freq, prefix) in zip([ghz, mhz, khz, hz], ["G", "M", "k", "H"]):
            cmd = f"{freq}{prefix}F1"
            nchar, resp = self.sendCommand(cmd, timeout = 0.015, capture_output = True)
            if nchar == -1 or resp != "A":
                print(resp)
                return 1
            
        return 0

