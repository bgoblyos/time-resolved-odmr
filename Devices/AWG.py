"""
Copyright (C) 2025 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import pyvisa


"""
Class for controlling Siglent SDG 1062X arbitrary waveform generator
Uses GPL-3 licensed code from https://github.com/AI5GW/SIGLENT,
copyright (C) 2022 Sebastian (AI5GW) <sebastian@baltic-lab.com>
"""
class SDG1060X():
    def __init__(self, rm, address, internal_oscillator = True):
        self.device = rm.open(address, query_delay=0.25)
        # increase timeout to 10s to allow large transfers
        self.device.timeout = 10000
        # set up clock source
        self.set_oscillator(internal_oscillator)
        
    def set_oscillator(self, internal):
        if internal:
            self.device.write("ROSC INT")
            self.device.write("ROSC 10MOUT,ON")