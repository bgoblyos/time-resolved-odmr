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
        [10,  True,  False, False],
        [15,  False, True,  False],
        [5,   False, True,  True ],
        [8,   True,  False, True ],
        [0.5, True,  True,  False],
        [2,   False, False, False],
        [0.1, True,  True,  True ],
        [2,   False, False, False],
        [10,  True,  False, False],
        [15,  False, True,  False],
        [5,   False, True,  True ],
        [8,   True,  False, True ],
        [0.5, True,  True,  False],
        [2,   False, False, False],
        [0.1, True,  True,  True ],
        [2,   False, False, False],
    ]
)

Devices.AWG.vis_sequence_equidistant(sequence)