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

import pyvisa
import pandas as pd
import numpy as np
import time
from tqdm import tqdm
from Devices.LockIn import SR830M
from Devices.LO import KuhnePLL
from Devices.PicoPulse import PicoPulse

class CW():
    def __init__(self, lo_addr, lock_addr, pico_addr):
        self.lo_addr = lo_addr
        self.lock_addr = lock_addr
        self.pico_addr = pico_addr
        self.setupDevices()
        self.idleSeq()
        
        
    def __del__(self):
        self.unloadDevices()
        
    def setupDevices(self):
        self.rm = pyvisa.ResourceManager()
        self.lo = KuhnePLL(self.lo_addr)
        self.lock = SR830M(self.rm, self.lock_addr)
        self.pico = PicoPulse(self.rm, self.pico_addr)
        
    def unloadDevices(self):
        self.lo = None
        self.lock = None
        self.pico = None
        self.rm.close()
        self.rm = None
        
    def refreshDevices(self):
        self.unloadDevices()
        self.setupDevices()
        
    def idleSeq(self, freq = 500):
        halft = round(1e9/(freq*2))
        seq = pd.DataFrame(
            columns = ["time", "ch1", "ch2", "ch3", "ch4"],
            data = [
                [halft, 1, 0, 0, 0],
                [halft, 0, 0, 0, 0]
            ]
        )
        
        self.pico.sendSequence(seq, cycle = False)
        self.idle = True
        
    def cwSeq(self, freq = 500):
        halft = round(1e9/(freq*2))
        seq = pd.DataFrame(
            columns = ["time", "ch1", "ch2", "ch3", "ch4"],
            data = [
                [halft, 1, 1, 1, 1],
                [halft, 0, 1, 0, 0]
            ]
        )
        
        self.pico.sendSequence(seq, cycle = False)
        self.idle = False
        
    def measureCW(self, freq, settle = 1, integrate = 5, srate = None, lockin_freq = 500, comment = ""):
        """
        Measures CW ODMR signal at a given frequency.

        Parameters
        ----------
        freq : float
            Microwave frequency in GHz.
        settle : float, optional
            Amount of time in seconds to wait before starting data acquisition. The default is 1.
        integrate : float, optional
            Duration of data acqusition is seconds. The default is 5.
        srate : float, optional
            Sampling rate of the lock-in amplifier. Set to None for automatic. The default is None.
        lockin_freq : float, optional
            Set lock-in reference frequency in Hz. The default is 500.
        comment : str, optional
            Attach a comment to the data point. The default is "".

        Returns
        -------
        dict
            Dictionary containing results and supplementary info.

        """
        self.lo.setGHz(freq)
        
        # If idle, start the CW sequence and mark that we wish to make it idle once we're done
        returnToIdle = False
        if self.idle:
            self.cwSeq(lockin_freq)
            returnToIdle = True
        
        time.sleep(settle)
        Rs, thetas = self.lock.multiRead(ch1 = "R", ch2 = "THETA", t = integrate, srate = srate)
        
        lockin_freq = self.lock.getFreq()
        
        if returnToIdle:
            self.idleSeq(lockin_freq)
        
        return {
            "freq_GHz": freq,
            "Rs_V": Rs,
            "Rmean": np.mean(Rs),
            "Rstd":  np.std(Rs),
            "thetas_deg": thetas,
            "settle_s": settle,
            "measure_s": integrate,
            "timestamp": time.time(),
            "lockin_freq_Hz": lockin_freq,
            "comment": comment
        }
        
        
    def iterateCW(self, fs, savedir = None, savename = "CW", lockin_freq = 500, shuffle = False, **kwargs):
        """
        Iterate over an array of frequencies and measure CW ODMR signal at them.

        Parameters
        ----------
        fs : array of floats
            Frequencies to iterate over.
        savedir : str, optional
            Save directory. If not None, dump result into a JSON file at the given directory. The default is None.
        savename : str, optional
            Stringto append to saved filename. The default is "CW".
        lockin_freq : float, optional
            Set lock-in reference frequency in Hz. The default is 500.
        shuffle : Bool, optional
            Whether or not to shuffle the array beforehand. Useful for eliminating centrain measurement artifacts. The default is False.
        **kwargs : TYPE
            Pass arguments to CW.measureCW(). The valid arguments are "settle", "integrate", "srate" and "comment".

        Returns
        -------
        df : pandas.DataFrame
            DataFrame with each row representing a measurement..

        """
 
        self.cwSeq(lockin_freq)
        tmp = []
        
        if shuffle:
            np.random.shuffle(fs)
            
        
        for f in tqdm(fs):
            tmp.append(self.measureCW(f, **kwargs))
        
        df = pd.DataFrame.from_dict(tmp)
        tmp = None
        
        if savedir is not None:
            ts = round(time.time())
            fname = f"{savedir}/{ts}_{savename}"
            df.to_json(fname)
        
        self.idleSeq(lockin_freq)
        return df
