"""
Copyright (C) 2025-2026 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import serial      # Serial communication
import time        # Timeout handling
import numpy as np # Math

"""
Kuhne MKU LO 8-13 PLL
"""
class KuhnePLL():
    def __init__(self, port, timeout = 1.0, legacy = False):
        self.device = None
        self.port = port
        self.connect_timeout = timeout
        self.legacy = legacy
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
            if self.legacy:
                cmd = f"{freq}{prefix}F1"
            else:
                cmd = f"{prefix}FR{freq}\r\n"
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
