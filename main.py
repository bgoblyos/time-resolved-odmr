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
import Devices.LockIn

import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time

#%%
awg1_addr = 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR' 
awg2_addr = 'USB0::0xF4EC::0x1103::SDG1XDDC801272::INSTR'
lock_addr = 'GPIB0::8::INSTR'
#%% Measure noise
rm = pyvisa.ResourceManager()
awg1 = Devices.AWG.SDG1062X(rm, 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR', internal_oscillator=True)
lock = Devices.LockIn.SR830M(rm, 'GPIB0::8::INSTR')

Rs = []
Xns = []
Yns = []
delays = [1] #np.linspace(1, 15000, 100)
for delay in delays:
    awg1.output(1, False)
    awg1.output(2, False)
    fl = lock.snap()["Ref"]
    sequence = pd.DataFrame(
        columns = ["time_us", "L", "I", "Q"],
        data = [
            [delay, False, False, False],
            [2, True, False, False],
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
    awg1.device.query("*OPC?")
    awg1.output(1, True)
    awg1.output(2, True)
    awg1.device.query("*OPC?")
    
    
    time.sleep(15)
    
    res1 = lock.snap()
    res2 = lock.snap(aux=True)
    
    Rs.append(res1["R"])
    Xns.append(res2["DISP1"])
    Yns.append(res2["DISP2"])
#%% T1
def T1(tau, ti, tr, settle = 10, integrate = 10, srate = 1e6):
    
    rm = pyvisa.ResourceManager()
    awg1 = Devices.AWG.SDG1062X(rm, awg1_addr, internal_oscillator=True)
    lock = Devices.LockIn.SR830M(rm, lock_addr)
    
    awg1.output(1, False)
    awg1.output(2, False)
    
    fl = lock.snap()["Ref"]
    delay = srate/fl/2 - ti
    
    sequence = pd.DataFrame(
        columns = ["length", "L", "I", "Q"],
        data = [
            [ti,    True,  False, False],
            [delay, False, False, False],
            [ti,    True,  False, False],
            [tau,   False, False, False],
            [tr,    True,  False, False],
        ]
    )
    
    Lp, Ln, I, Q = Devices.AWG.seq_to_waveforms(sequence)
    
    
    awg1.set_waveform_exact(
         1, Lp, samplerate=srate, amp = 20, name = "Lp")
    awg1.set_waveform_exact(
         2, Ln, samplerate=srate, amp = 20, name = "Ln")
     
    # Set up burst and enable AWG outputs
    awg1.burst_ext(1)
    awg1.burst_ext(2)
    awg1.device.query("*OPC?")
    awg1.output(1, True)
    awg1.output(2, True)
    awg1.device.query("*OPC?")
    
    # Clear buffer and set up lock-in data collection
    lock.device.write("TSTR")
    lock.device.write("SRAT 7")
    lock.device.write("SEND 0")
    lock.device.write("PAUS;REST")
    # Wait for system to settle and trigger the data collection
    time.sleep(settle)
    lock.device.write("TRIG")
    
    # Wait for data to be collected
    time.sleep(integrate)
    
    # Stop data collection
    lock.device.write("PAUS")
    
    # Retrieve data
    data = list(map(float, lock.device.query(f"TRCA?1,0,{integrate * 8}").split(',')[:-1]))
    mean = np.mean(data)
    std = np.std(data)
    resp = lock.snap()
    
    rm.close()
    
    return {
        "Rs": data,
        "Rmean": mean,
        "Rstd": std,
        "Tinit": ti/srate,
        "Tread": tr/srate,
        "Tau": tau/srate,
        "Theta": resp["Theta"],
        "X": resp["X"],
        "Y": resp["Y"],
        "Fref": fl
    }
    

def T1iterated(taus, tis, trs, savedir = None, **kwargs):

    results = []
    
    for tau in taus:
        for ti in tis:
            for tr in trs:
                results.append(T1(tau, ti, tr, **kwargs))
                
    data = pd.DataFrame.from_dict(results)

    if savedir is not None:
        timestamp = round(time.time())
        data.to_json(f"{savedir}/{timestamp}.json")
    
    return data