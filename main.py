#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

#%% Imports
import Devices.AWG

import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

#%% Device setup
rm = pyvisa.ResourceManager()

sequence = pd.DataFrame(
    columns = ["time_us", "L", "I", "Q"],
    data = [
        [0.1,  True,  False, False],
        [10,  False,  False, False],
        [20,  True,  False, False],
        [10,  False,  False, False],
        [30,  True,  False, False],
    ]
)

#AWG1 = Devices.AWG.SDG1060X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR')
#AWG2 = Devices.AWG.SDG1060X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801272::INSTR')

#L, I, Q = Devices.AWG.seq_to_waveforms(sequence, 30e6)

#sent = AWG1.set_waveform(L, 1, samplerate=30e6, amp = 5, name = "test")
#sent

AWG = Devices.AWG.SDG1060X(None, 'DUMMY')

AWG.burst_int(1)
AWG.burst_ext(2)