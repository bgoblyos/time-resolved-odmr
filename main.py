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
import time

#%% Device setup
rm = pyvisa.ResourceManager()

awg1 = Devices.AWG.SDG1062X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR', internal_oscillator=True)
#awg2 = Devices.AWG.SDG1062X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801272::INSTR', internal_oscillator=False)

lock = rm.open_resource('GPIB0::8::INSTR')
float(lock.query("SNAP ? 3,4").split(',')[0])

#%% Upload waveforms

tr = 3
ti = 20
fl = 66.14

taus = np.linspace(40,2000,30)
results = np.zeros(taus.shape)
thetas = np.zeros(taus.shape)
for i, tau in enumerate(taus):
    print(f"Begin step {i+1}, tau = {tau}")
    sequence = pd.DataFrame(
        columns = ["time_us", "L", "I", "Q"],
        data = [
            [ti, True, False, False],
            [5e5/fl - ti,  False,  True, True],
            [ti, True, False, False],
            [tau, False, False, False],
            [tr, True, False, False],
            [10, False, False, False],
        
        ]
    )

    Lp, Ln, I, Q, samplerate = Devices.AWG.seq_to_waveforms(sequence, fl)


    awg1.set_waveform_exact(
        1, Lp, samplerate=samplerate, amp = 20, name = "Lp")
    awg1.set_waveform_exact(
        2, Ln, samplerate=samplerate, amp = 20, name = "Ln")

    awg1.burst_ext(1)
    awg1.burst_ext(2)
    
    lock.write("OFLT 0")
    time.sleep(1)
    lock.write("OFLT 9")
    time.sleep(4)
    resp = lock.query("SNAP ? 3,4").split(',')
    results[i] = float(resp[0])
    thetas[i] = float(resp[1])
    
plt.plot(taus, results)
plt.xlabel("Tau (us)")
plt.ylabel("Lock-in signal (mV)")
plt.show()