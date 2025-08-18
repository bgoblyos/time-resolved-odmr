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

LIQ = Devices.AWG.LIQ_SDG1062X(
    rm,
    addr1 = 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR',
    addr2 = 'USB0::0xF4EC::0x1103::SDG1XDDC801272::INSTR',
    delay = 3.15e-7
)

#%% Upload waveforms

sequence = pd.DataFrame(
    columns = ["time_us", "L", "I", "Q"],
    data = [
        [2000,  True,  True, True],
        [100,  True,  False, False],
        [100,  False,  True, False],
        [100,  False,  False, True],
        #[10,  True,  True, True],
    ]
)


sequence = pd.DataFrame(
    columns = ["time_us", "L", "I", "Q"],
    data = [
        [1000,  True,  True, True],
        [200,  False,  False, False],
        [200,  True,  True, True],
        [1000,  False,  False, False],
    ]
)

L, I, Q = LIQ.set_sequence(sequence, burst_period=0.001)
