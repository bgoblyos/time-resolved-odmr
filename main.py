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
from Devices.LO import KuhnePLL


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
osc_addr = 'COM4'
counter_addr = 'GPIB0::2::INSTR'
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
#%% Rabi definitions


def rabi(mw, mw_freq = None, settle = 1, integrate = 1, comment = "None"):
    rm = pyvisa.ResourceManager()
    lock = Devices.LockIn.SR830M(rm, lock_addr)
    pico = PicoPulse(rm, pico_addr)
    sweeper = Devices.Sweeper.HP83752A(rm, sweeper_addr)
    
    if mw_freq is not None:
        sweeper.setCW(mw_freq)
    
    laser_on =  90000   # 90 us
    laser_off = 10000   # 10 ms
    cycles = 100
    
    temp = []
    
    # Microwave cycle
    for i in range(cycles):
        temp.append([laser_off-mw, 1, 0, 0, 0])
        temp.append([mw,           1, 0, 1, 1])
        temp.append([laser_on,     1, 1, 0, 0])
        
    # Reference cycle
    for i in range(cycles):
        temp.append([laser_off-mw, 0, 0, 0, 0])
        temp.append([mw,           0, 0, 0, 0])
        temp.append([laser_on,     0, 1, 0, 0])
    
    sequence = pd.DataFrame(
        columns = ["time", "ch1", "ch2", "ch3", "ch4"],
        data = temp
    )
    
    pico.sendSequence(sequence, cycle = False)

    
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
        "seq": sequence,
        #"halfperiod_ns": halft,
        #"padding_ns": padding,
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
mws = np.arange(20, 5000, 100)
np.random.shuffle(mws)
#mws = np.flip(mws)

result = rabi_iterated(
    mws,
    [2.7666],
    savedir = "E:/Rabi/",
    settle = 2,
    integrate = 3,
    comment = "90% duty cycle, 10 dBm on sweeper",
)
plt.errorbar(result.mw_ns, 1000*result.Rmean, yerr = result.Rstd, fmt=".")
plt.xlabel("Microwave cycle (ns)")
plt.ylabel("Lock-in signal (mV)")
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
        [1e6, 1, 1, 0, 0],
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

res = pico.sendSequence(idle_seq, cycle = False)

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
fs = np.linspace(2.76, 2.77, 120)
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
#%% Kuhne LO
from Devices.LO import KuhnePLL

osc = KuhnePLL(osc_addr)

osc.setGHz(2.7666)
osc.sendCommand("A1")
    
del osc

#%%
def readPower(freq_hz, wait = 5.0):
   
    osc = KuhnePLL(osc_addr)
    osc.setHz(freq_hz) 
    del osc
    
    time.sleep(wait)
    
    freq_mhz = round(freq_hz / 1e6)
    
    rm = pyvisa.ResourceManager()
    counter = rm.open_resource(counter_addr)
    counter.read_termination = '\r'
    counter.write("PA")
    counter.write("BR")
    counter.write("FH 7000")
    counter.write("FL 950")
    counter.write(f"CF {freq_mhz}")
    resp = counter.read()
    rm.close()
    freq_meas, power = [float(x.strip()) for x in resp.split(',')]
    return {
        "target_Hz": freq_hz,
        "meas_Hz": freq_meas,
        "meas_dBm": power
    }

freqs = np.linspace(1e9, 6.85e9, 5000)
temp = []

for i in tqdm.tqdm(freqs):
    temp.append(readPower(i, wait = 12))

df = pd.DataFrame.from_dict(temp)
name = "Kuhne_direct_highres"
timestamp = round(time.time())
df.to_json(f"E:/Oscillator/{name}_{timestamp}.json")
#%%
plt.scatter(df.target_Hz, df.meas_dBm)
plt.xlim(0.95e9,6.9e9)

#%%
import scipy as sc
mask = np.abs(df.target_Hz - df.meas_Hz) < 1e9
#plt.scatter(df.meas_Hz[mask], df.meas_dBm[mask])

filtered = sc.ndimage.median_filter(df.meas_dBm[mask], size = 50)
plt.scatter(df.meas_Hz[mask], filtered)
plt.xlim(2.5e9, 3e9)

# %%
def readPowerAlt(freq_hz, wait = 5.0):
   
    rm= pyvisa.ResourceManager()
    sweeper = Devices.Sweeper.HP83752A(rm, sweeper_addr)
        
    sweeper.setCW(freq_hz/1e9)
    
    time.sleep(wait)
    
    freq_mhz = round(freq_hz / 1e6)
    
    rm = pyvisa.ResourceManager()
    counter = rm.open_resource(counter_addr)
    counter.read_termination = '\r'
    counter.write("PA")
    counter.write("BR")
    counter.write("FH 7000")
    counter.write("FL 950")
    counter.write(f"CF {freq_mhz}")
    resp = counter.read()
    rm.close()
    freq_meas, power = [float(x.strip()) for x in resp.split(',')]
    return {
        "target_Hz": freq_hz,
        "meas_Hz": freq_meas,
        "meas_dBm": power
    }

freqs = np.linspace(1e9, 20e9, 720)
temp = []

for i in tqdm.tqdm(freqs):
    temp.append(readPowerAlt(i, wait = 5))

df = pd.DataFrame.from_dict(temp)
name = "sweeper_0dBm_female_male_SMA"
timestamp = round(time.time())
df.to_json(f"E:/Oscillator/{name}_{timestamp}.json")
plt.scatter(df.target_Hz, df.meas_dBm)
