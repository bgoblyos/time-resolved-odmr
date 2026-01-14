# Copyright (C) 2025 Bence Göblyös

import serial      # Serial communication
import time        # Timeout handling
import numpy as np # Math

"""
Kuhne MKU LO 8-13 PLL
"""
class KuhnePLL():
    def __init__(self, port, timeout = 1.0):
        self.device = None
        self.port = port
        self.connect_timeout = timeout
        self.connect()
        
    def __del__(self):
        self.device.close()
        
    def connect(self):
        try:
            self.device = serial.Serial(
                port = self.port,
                baudrate = 115200,
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout = self.connect_timeout,
            )
            return True
        except serial.SerialException as err:
            print(f"Failed to connect to oscillator with reason: {err}")
            return False

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

    def setHz(self, val):
        # TODO: Soft fail if device is None
        hz = str(round((np.floor(val) % 1000))).zfill(3)
        khz = str(round(np.floor(val*1e-3) % 1000)).zfill(3)
        mhz = str(round(np.floor(val*1e-6) % 1000)).zfill(3)
        ghz = str(round(np.floor(val*1e-9) % 1000)).zfill(3)

        
        for (freq, prefix) in zip([ghz, mhz, khz, hz], ["G", "M", "k", "H"]):
            cmd = f"{freq}{prefix}F1"
            nchar, resp = self.sendCommand(cmd, timeout = 0.015, capture_output = True)
            if nchar == -1 or resp != "A":
                print(resp)
                return False
            
        return True
    
    def setkHz(self, val):
        return self.setHz(val*1e3)
    
    def setMHz(self, val):
        return self.setHz(val*1e6)
    
    def setGHz(self, val):
        return self.setHz(val*1e9)
