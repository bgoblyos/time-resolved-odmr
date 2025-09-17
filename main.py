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

awg1 = Devices.AWG.SDG1062X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR', internal_oscillator=True)
#awg2 = Devices.AWG.SDG1062X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801272::INSTR', internal_oscillator=False)

#%% Upload waveforms

sequence = pd.DataFrame(
    columns = ["time_us", "L", "I", "Q"],
    data = [
        [0.5e6 / 247.2, True, False, False],
        [40,  False,  True, True],
    ]
)

L, I, Q, samplerate = Devices.AWG.seq_to_waveforms(sequence, 247.2)


awg1.set_waveform_exact(
    1, L, samplerate=samplerate, amp = 1, name = "L")

awg1.burst_ext(1)