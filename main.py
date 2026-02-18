#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

#%% Imports
from Devices.LockIn import SR830M
from Devices.PicoPulse import PicoPulse
from Devices.LO import KuhnePLL


import pyvisa                    # Required for communication
import matplotlib.pyplot as plt  # Plots
import numpy as np               # Maths
import pandas as pd              # DataFrames
import time                      # Delays
import tqdm                      # Progress bars (use 'for i in tqdm.tqdm(iter)')

#%% Constants
lockin_addr = 'GPIB0::8::INSTR'
sweeper_addr = 'GPIB0::11::INSTR'
pico_addr = 'ASRL3::INSTR'
osc_addr = 'COM4'
counter_addr = 'GPIB0::2::INSTR'

pico_pins = {
    'lockin': 'ch1',
    'Q': 'ch2',
    'I': 'ch3',
    'laser': 'ch4'
}

#%% Turn off laser
idle_seq = pd.DataFrame(
        columns = ['time', 'lockin', 'laser'],
        data = [
            [1e6, 0, 0],
            [1e6, 1, 0],
        ]
    )

rm = pyvisa.ResourceManager()
pico = PicoPulse(rm, pico_addr, pico_pins)
pico.sendSequence(idle_seq)
rm.close()

#%% Turn on laser for adjustment
idle_seq = pd.DataFrame(
        columns = ['time', 'lockin', 'laser'],
        data = [
            [1e6, 0, 1],
            [1e6, 1, 1],
        ]
    )

rm = pyvisa.ResourceManager()
pico = PicoPulse(rm, pico_addr, pico_pins)
pico.sendSequence(idle_seq)
rm.close()

#%% Lock-in amplifier demo

rm = pyvisa.ResourceManager()
lockin = SR830M(rm, lockin_addr)

# Read single values
x, y, r, theta = lockin.snapshot(['x', 'y', 'r', 'theta'])
reference, aux1 = lockin.snapshot(['ref', 'aux1'])

# Sample X and Y for 8 seconds with an automatic sample rate
# (calculated from time constant)
xs, ys = lockin.multiRead('x', 'y', 8)

# Sample AUX4 for 10 seconds at 4 Hz
# Setting channel 1 to None speeds up readout
_, aux4s = lockin.multiRead(None, 'aux4', 10, 4)

rm.close()

#%% MW oscillator demo
osc = KuhnePLL(osc_addr)
osc.setGHz(2.87)

del osc

