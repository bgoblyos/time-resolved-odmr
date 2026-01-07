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
import Devices.Sweeper
from Devices.PicoPulse import PicoPulse

import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import tqdm

#%%
awg1_addr = 'USB0::0xF4EC::0x1103::SDG1XDDC801291::INSTR' 
awg2_addr = 'USB0::0xF4EC::0x1103::SDG1XDDC801272::INSTR'
lock_addr = 'GPIB0::8::INSTR'
sweeper_addr = 'GPIB0::11::INSTR'
pico_addr = 'ASRL3::INSTR'
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
def T1(tau, ti, tr, halft = 1e7, settle = 10, integrate = 10, comment = ""):
    
    rm = pyvisa.ResourceManager()
    pico = PicoPulse(rm, pico_addr)
    lock = Devices.LockIn.SR830M(rm, lock_addr)
        
    sequence = pd.DataFrame(
        columns = ["time", "ch1", "ch2", "ch3", "ch4"],
        data = [
            [ti,              1, 1, 0, 0],
            [halft-ti,        1, 0, 0, 0],
            [ti,              0, 1, 0, 0],
            [tau,             0, 0, 0, 0],
            [tr,              0, 1, 0, 0],
            [halft-ti-tr-tau, 0, 0, 0, 0],
        ]
    )
     
    pico.sendSequence(sequence, cycle = False)
    
    #TODO: Set display 1 to R programmatically
    
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
        "Tinit": ti,
        "Tread": tr,
        "Tau": tau,
        "Theta": resp["Theta"],
        "X": resp["X"],
        "Y": resp["Y"],
        "Fref": 1e9/halft,
        "Comment": comment,
    }
    

def T1iterated(taus, tis, trs, savedir = None, **kwargs):

    results = []
    pbar = tqdm.tqdm(total = len(taus)*len(tis)*len(trs))
    
    for tau in taus:
        for ti in tis:
            for tr in trs:
                results.append(T1(tau, ti, tr, **kwargs))
                pbar.update(1)
                
    data = pd.DataFrame.from_dict(results)
    pbar.close()
    
    if savedir is not None:
        timestamp = round(time.time())
        data.to_json(f"{savedir}/{timestamp}.json")
    
    return data
#%%
result = T1iterated(
    np.geomspace(1e3,6e6,20),
    [50e3], #[5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    [10e3], #[1,2,3,4,5,6,7,8,9,10],
    savedir = "E:/T1",
    settle = 5,
    integrate = 25,
    comment = "40 dB detector gain, high reserve"
)
plt.errorbar(result.Tau, result.Rmean, yerr = result.Rstd)
plt.xscale("log")
#%%
plt.errorbar(result.Tau, result.Rmean, yerr = result.Rstd)
#plt.ylim(1.7e-5, 1.9e-5)
plt.xscale("log")
plt.show()
#%%
rm = pyvisa.ResourceManager()
pico = rm.open_resource(pico_addr)

def wrap_query(str):
    print(f"Query: {repr(str)}")
    resp = pico.query(str)
    print(f"Response: {repr(resp)}")
    return resp

for mw in [20,30,40,50,60,70,80,90,100]:
    # Lock-in reference signal
    halft = 1000000
    wait1 = 13000
    #mw = 20
    seq = f"{wait1},1,{mw},3,{halft-mw-wait1},1,{halft},0"
    wrap_query(f"PULSE 0 {1 << 32 - 1} {seq}")
    time.sleep(1)

    
# awg1 = Devices.AWG.SDG1062X(rm, awg1_addr, internal_oscillator=True)
# lock = Devices.LockIn.SR830M(rm, lock_addr)

# #awg1.output(1, False)
# #awg1.output(2, False)

# srate = 8.2e6
# fl = lock.snap()["Ref"]
# ti = 100 # 10 us
# delay = srate/fl/2 - ti

# sequence = pd.DataFrame(
#     columns = ["length", "L", "I", "Q"],
#     data = [
#         [ti,    True, False, False],
#         [delay, False, False, False],
#         [ti,    True, False, False],
#     ]
# )

# Lp, Ln, I, Q = Devices.AWG.seq_to_waveforms(sequence)


# awg1.set_waveform_exact(
#      1, Lp, samplerate=srate, amp = 20, name = "Lp")
# awg1.set_waveform_exact(
#      2, Ln, samplerate=srate, amp = 20, name = "Ln")
 
# # Set up burst and enable AWG outputs
# awg1.burst_ext(1)
# awg1.burst_ext(2)
# awg1.device.query("*OPC?")
# #awg1.output(1, True)
# #awg1.output(2, True)
# awg1.device.query("*OPC?")


rm.close()
#%% Rabi definitions


def rabi(mw, mw_freq = None, settle = 1, integrate = 1, comment = "None"):
    rm = pyvisa.ResourceManager()
    pico = rm.open_resource(pico_addr)
    lock = Devices.LockIn.SR830M(rm, lock_addr)
    sweeper = Devices.Sweeper.HP83752A(rm, sweeper_addr)
    
    if mw_freq is not None:
        sweeper.setCW(mw_freq)
    
    # Lock-in reference signal
    #halft = 1000000
    #wait1 = 50
    #mw = 20
    #seq = f"{halft-mw-wait1},1,{mw},3,{wait1},1,{halft},0"
    
    laser_on = 90000
    laser_off = 10000
    padding = 500
    delay = laser_on + laser_off
    halft = 1000000
    if mw + padding + 40 > laser_off:
        return {"Errors" : ["Microwave cycle too long"]}
    
    if mw >= 20:
        mw_seq = f"{laser_on},1,{laser_off - mw - padding},1,{mw},3,{padding},1,"
        seq = f"{delay},1,{9 * mw_seq}{halft},0"
    else:
        seq = f"{halft},1,{halft},0"    
    
    pico.query(f"PULSE 0 {1 << 32 - 1} {seq}")
    
    # Clear buffer and set up lock-in data collection
    lock.device.write("TSTR")
    #lock.device.write("SRAT 7") # 8 Hz
    # TODO: Implement this by sending the desired sample rate
    lock.device.write("SRAT 9") # 32 Hz
    lock.device.write("SEND 0")
    lock.device.write("PAUS;REST")
    # Wait for system to settle and trigger the data collection
    time.sleep(settle)
    lock.device.write("TRIG")
    
    # Wait for data to be collected
    time.sleep(integrate + 0.125)
    
    # Stop data collection
    lock.device.write("PAUS")
    
    # Retrieve data
    Rs = lock.readBuffer(1, 0, integrate * 32)
    Thetas = lock.readBuffer(2, 0, integrate * 32)
    mean = np.mean(Rs)
    std = np.std(Rs)
    resp = lock.snap()
    
    mw_freq = sweeper.getCW()
    mw_power = sweeper.readPowerLevel()
    
    #TODO: Read errors from sweeper
    
    rm.close()
    
    return {
        "Rs": Rs,
        "Rmean": mean,
        "Rstd": std,
        "mw_ns": mw,
        "Thetas": Thetas,
        "settle_s": settle,
        "integrate_s": integrate,
        "seq": seq,
        "halfperiod_ns": halft,
        "padding_ns": padding,
        "Fref_Hz": resp["Ref"],
        "comment": comment,
        "mw_freq_Hz": mw_freq,
        "mw_power_dBm": mw_power,
        "errors": [],
    }

def rabi_iterated(mws, freqs = [None], savedir = None, **kwargs):

    results = []
    pbar = tqdm.tqdm(total = len(mws) * len(freqs))
    
    for freq in freqs:
        for mw in mws:
            results.append(rabi(mw, mw_freq = freq, **kwargs))
            pbar.update(1)
                
    data = pd.DataFrame.from_dict(results)
    pbar.close()
    
    if savedir is not None:
        timestamp = round(time.time())
        data.to_json(f"{savedir}/{timestamp}.json")
    
    return data
    
#%%
mws = np.arange(10, 6000, 10)
#np.random.shuffle(mws)
mws = np.flip(mws)

result = rabi_iterated(
    mws,
    [2.6051], #np.linspace(2.6051-0.25, 2.6051 + 0.25, 3), #
    savedir = "E:/Rabi/",
    settle = 0.5,
    integrate = 1,
    comment = "Split resonance, 20 dB attenuator before amp",
)
plt.errorbar(result.mw_ns, result.Rmean, yerr = result.Rstd)
result

#%% CW
def CW(start, stop):
    rm = pyvisa.ResourceManager()
    pico = PicoPulse(rm, pico_addr)
    lock = Devices.LockIn.SR830M(rm, lock_addr)
    sweeper = Devices.Sweeper.HP83752A(rm, sweeper_addr)
    
    sweep_time = 100
    

    CW_seq = pd.DataFrame(
        columns = ["time", "ch1", "ch2", "ch3", "ch4"],
        data = [
            [1e6, 1, 1, 1, 1],
            [1e6, 0, 1, 0, 0]
        ]
    )

    pico.sendSequence(CW_seq, cycle = False)
    
    # Clear buffer and set up lock-in data collection
    lock.device.write("TSTR")
    lock.device.write("SRAT 7") # 8 Hz
    lock.device.write("SEND 0")
    lock.device.write("PAUS;REST")
    
    # Set up sweeper
    sweeper.setupSweep(start, stop, sweep_time)
    
    # Wait for system to settle and trigger the sweep
    time.sleep(1)
    sweeper.startSweep()
    
    # Wait for data to be collected
    time.sleep(sweep_time + 1)
    
    # Stop data collection
    lock.device.write("PAUS")
    
    # Retrieve data
    Rs = list(map(float, lock.device.query(f"TRCA?1,0,{sweep_time * 8}").split(',')[:-1]))
    thetas = list(map(float, lock.device.query(f"TRCA?2,0,{sweep_time * 8}").split(',')[:-1]))
    freqs = np.linspace(start , stop, len(Rs), endpoint=False)
    rm.close()
    
    return freqs, Rs, thetas

#%%
freq, Rs, thetas = CW(2.72, 2.9)
plt.plot(freq, Rs)
plt.xlabel("Microwave frequency (GHz)")
plt.ylabel("Lock-in signal (V)")

df = pd.DataFrame(columns=["freqs", "R", "theta"], data = np.array([freq, Rs, thetas]).T)
#df.to_json("E:/CW/Rabi/pulsed_laser_magnet_overview.json")
plt.plot(df.freqs, df.R)
#%%
plt.scatter(df.freqs, df.R)
plt.xlim(2.72, 2.9)

#%%
rm =  pyvisa.ResourceManager()
pico = rm.open_resource(pico_addr)

seq = "1000000,3,1000000,3"
pico.query(f"PULSE 0 {1 << 32 - 1} {seq}")

rm.close()
#%% Sweeper diagnostics
rm = pyvisa.ResourceManager()

sweeper = Devices.Sweeper.HP83752A(rm, sweeper_addr)

print(sweeper.device.query("SYST:ERR?"))

rm.close()

#%%

CW_seq = pd.DataFrame(
    columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    data = [
        [1e6, 1, 1, 1, 1],
        [1e6, 0, 1, 0, 0]
    ]
)


idle_seq = pd.DataFrame(
    columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    data = [
        [1e6, 1, 0, 0, 0],
        [1e6, 0, 0, 0, 0]
    ]
)

laser_seq = pd.DataFrame(
    columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    data = [
        [1e6, 1, 1, 0, 0],
        [1e6, 0, 1, 0, 0]
    ]
)

transient_seq = pd.DataFrame(
    columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    data = [
        [500, 0, 1, 0, 0],
        [500, 0, 0, 0, 0]
    ]
)

laser_noise_seq = pd.DataFrame(
    columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    data = [
        [1e6, 1, 0, 0, 0],
        [1e6, 1, 1, 0, 0],
        [1e6, 0, 0, 0, 0],
        [1e6, 0, 1, 0, 0],
    ]
)

pl_lock_seq = pd.DataFrame(
    columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    data = [
        [1e6, 0, 0, 0, 0],
        [1e6, 1, 1, 0, 0],
    ]
)

#%%
rm = pyvisa.ResourceManager()
pico = PicoPulse(rm, pico_addr)

res = pico.sendSequence(laser_seq, cycle = False)

rm.close()
res

# %% CW, no sweep

def CWalt(f, settle = 10, integrate = 10, comment = ""):
    
    rm = pyvisa.ResourceManager()
    # pico = PicoPulse(rm, pico_addr)
    lock = Devices.LockIn.SR830M(rm, lock_addr)
    sweeper = Devices.Sweeper.HP83752A(rm, sweeper_addr)
        
    sweeper.setCW(f)
    sweeper.powerOn()
    
    # CW_seq = pd.DataFrame(
    #     columns = ["time", "ch1", "ch2", "ch3", "ch4"],
    #     data = [
    #         [1e6, 1, 1, 1, 1],
    #         [1e6, 0, 1, 0, 0]
    #     ]
    # )

    # pico.sendSequence(CW_seq, cycle = False)
    
    #TODO: Set display 1 to R programmatically
    
    # Clear buffer and set up lock-in data collection
    lock.device.write("TSTR")
    lock.device.write("SRAT 9") # 32 Hz
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
    data = lock.readBuffer(1, 0, integrate * 32)
    mean = np.mean(data)
    std = np.std(data)
    resp = lock.snap()
    
    sweeper.powerOff()
    
    rm.close()
    
    return {
        "Rs": data,
        "Rmean": mean,
        "Rstd": std,
        "f": f,
        "Theta": resp["Theta"],
        "X": resp["X"],
        "Y": resp["Y"],
        "Comment": comment,
    }
    

def picoIdle():
    idle_seq = pd.DataFrame(
        columns = ["time", "ch1", "ch2", "ch3", "ch4"],
        data = [
            [1e6, 1, 0, 0, 0],
            [1e6, 0, 0, 0, 0]
        ]
    )
    
    rm = pyvisa.ResourceManager()
    pico = PicoPulse(rm, pico_addr)
    pico.sendSequence(idle_seq, cycle = False)
    rm.close()


def picoCW():
    CW_seq = pd.DataFrame(
        columns = ["time", "ch1", "ch2", "ch3", "ch4"],
        data = [
            [1e6, 1, 1, 1, 1],
            [1e6, 0, 1, 0, 0]
            ]
        )
    
    rm = pyvisa.ResourceManager()
    pico = PicoPulse(rm, pico_addr)
    pico.sendSequence(CW_seq, cycle = False)
    rm.close()

def CWiterated(fs, savedir = None, **kwargs):

    picoCW()

    results = []
    pbar = tqdm.tqdm(total = len(fs))
    
    for f in fs:
        results.append(CWalt(f, **kwargs))
        pbar.update(1)
                
    data = pd.DataFrame.from_dict(results)
    pbar.close()
    
    picoIdle()
    
    if savedir is not None:
        timestamp = round(time.time())
        data.to_json(f"{savedir}/{timestamp}.json")
    
    return data

#%%
fs = np.linspace(2.675, 3.1, 36000)
#fs = np.linspace(2.725, 2.750, 100)
np.random.shuffle(fs)

result = CWiterated(
    fs,
    savedir = "E:/CW/Hyperfine/",
    settle = 0.25,
    integrate = 0.75,
    comment = "15 mW laser, -15 dBm sweeper",
)
plt.errorbar(result.f, result.Rmean, yerr = result.Rstd, fmt = ".")
result