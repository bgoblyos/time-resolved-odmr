"""
Copyright (C) 2026 Bence Göblyös

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
from Devices.PicoPulse import PicoPulse

class T1():
    def __init__(self, lock_addr, pico_addr, pico_pins):
        """
        Initialize T1 experiment.

        Parameters
        ----------
        lock_addr : str
            VISA address of the lock-in amplifier.
        pico_addr : str
            VISA address of the pico-pulse device.
        pico_pins : dict
            Pin definitions for the pico-pulse device. Must map the keys
            'lockin' and 'laser' to their respective channels.

        Returns
        -------
        None.

        """
        self.lock_addr = lock_addr
        self.pico_addr = pico_addr
        self.pico_pins = pico_pins
        self.setupDevices()
        self.idleSeq()
        
    def __del__(self):
        self.unloadDevices()
        
    def setupDevices(self):
        self.rm = pyvisa.ResourceManager()
        self.lock = SR830M(self.rm, self.lock_addr)
        self.pico = PicoPulse(self.rm, self.pico_addr, self.pico_pins)
        
    def unloadDevices(self):
        self.idleSeq() # Turn off laser before unloading the device
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
             columns = ["time", "lockin", "laser"],
             data = [
                 [halft, 1, 0],
                 [halft, 0, 0]
             ]
         )
         
         self.pico.sendSequence(seq, cycle = False)
         self.idle = True
         
    def T1seq(self, tau, init = 50e3, readout = 10e3, freq = 64):
        """
        Generate and send T1 sequence.

        Parameters
        ----------
        tau : int
            Time to wait between initialization and readout in nanoseconds.
        init : int, optional
            Initialization pulse length in nanoseconds. The default is 50e3 (50 us).
        readout : int, optional
            Readout pulse length in nanoseconds. The default is 10e3 (10 us).
        freq : float, optional
            Lock-in frequency in Hz. The default is 64.

        Raises
        ------
        Exception
            An exception is raised if the desired sequence cannot be
            constructed because the padding length would become negative.

        Returns
        -------
        None.

        """
        
        halft = round(1e9/(freq*2))
        tpad = halft - init - readout - tau
        if tpad < 20:
            raise Exception('Cannot generate T1 sequence, padding is too short. Consider decreasing the lock-in frequency.')
             
        # Note: the sequence contains redundant pulses. This is to compensate any rounding errors,
        # i.e. tau + readout may not be exactly as long as tau and readout separately.
        seq = pd.DataFrame(
             columns = ["time", "lockin", "laser"],
             data = [
                 [init,    1, 1],
                 [tau,     1, 0],
                 [readout, 1, 1],
                 [tpad,    1, 0],
                 [init,    0, 1],
                 [tau,     0, 0],
                 [readout, 0, 0],
                 [tpad,    0, 0]
             ]
         )
         
        self.pico.sendSequence(seq, cycle = False)
        self.idle = False
        
    def measureT1(self, tau, init = 50e3, readout = 10e3, settle = 1,
                  integrate = 5, srate = None, lockin_freq = 64, comment = ""):
        """
        Measure a single T1 sequence.

        Parameters
        ----------
        tau : int
            Time to wait between initialization and readout in nanoseconds.
        init : int, optional
            Initialization pulse length in nanoseconds. The default is 50e3 (50 us).
        readout : int, optional
            Readout pulse length in nanoseconds. The default is 10e3 (10 us).
        settle : float, optional
            Amount of time in seconds to wait before starting data acquisition. The default is 1.
        integrate : float, optional
            Duration of data acqusition is seconds. The default is 5.
        srate : float, optional
            Sampling rate of the lock-in amplifier. Set to None for automatic. The default is None.
        lockin_freq : float, optional
            Set lock-in reference frequency in Hz. The default is 64.
        comment : str, optional
            Attach a comment to the data point. The default is "".

        Returns
        -------
        dict
            Dictionary containing results and supplementary info.

        """
        
        returnToIdle = self.idle
            
        self.T1seq(tau, init = init, readout = readout, freq = lockin_freq)
        
        time.sleep(settle)
        Rs, thetas = self.lock.multiRead(ch1 = "R", ch2 = "THETA", t = integrate, srate = srate)
        
        lockin_freq_measured = self.lock.getFreq()
        
        if returnToIdle:
            self.idleSeq(lockin_freq)
        
        return {
            "tau_ns": tau,
            "init_ns": init,
            "readout_ns": readout,
            "Rs_V": Rs,
            "Rmean": np.mean(Rs),
            "Rstd":  np.std(Rs),
            "thetas_deg": thetas,
            "settle_s": settle,
            "measure_s": integrate,
            "timestamp": time.time(),
            "lockin_freq_set_Hz": lockin_freq,
            "lockin_freq_measured_Hz": lockin_freq_measured,
            "comment": comment
        }

    def iterateT1(self, taus, init = 50e3, readout = 10e3, savedir = None, savename = "T1", lockin_freq = 64, shuffle = False, **kwargs):
        """
        Iterate over an array of taus and measure T1 signal at them.

        Parameters
        ----------
        taus : array of floats
            List of time to wait between initialization and readout in nanoseconds.
        init : int, optional
            Initialization pulse length in nanoseconds. The default is 50e3 (50 us).
        readout : int, optional
            Readout pulse length in nanoseconds. The default is 10e3 (10 us).
        savedir : str, optional
            Save directory. If not None, dump result into a JSON file at the given directory. The default is None.
        savename : str, optional
            String to append to saved filename. The default is "T1".
        lockin_freq : float, optional
            Set lock-in reference frequency in Hz. The default is 64.
        shuffle : Bool, optional
            Whether or not to shuffle the array beforehand. Useful for eliminating centrain measurement artifacts. The default is False.
        **kwargs : TYPE
            Pass arguments to T1.measureT1(). The valid arguments are "settle", "integrate", "srate" and "comment".

        Returns
        -------
        df : pandas.DataFrame
            DataFrame with each row representing a measurement.

        """
        
        if round(1e9/(lockin_freq*2)) - init - readout - np.max(taus) < 20:
            raise Exception('At least one value of tau is too large for the given lockin frequency.')
 
        tmp = []
        
        if shuffle:
            np.random.shuffle(taus)
            
        
        for tau in tqdm(taus):
            tmp.append(self.measureT1(tau, init = init, readout = readout, lockin_freq = lockin_freq, **kwargs))
        
        df = pd.DataFrame.from_dict(tmp)
        tmp = None
        
        if savedir is not None:
            ts = round(time.time())
            fname = f"{savedir}/{ts}_{savename}"
            df.to_json(fname)
        
        self.idleSeq(lockin_freq)
        return df