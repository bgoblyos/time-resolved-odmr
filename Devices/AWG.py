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

import pyvisa
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


"""
Class for controlling Siglent SDG 1062X arbitrary waveform generator
Uses modified GPL-3 licensed code from https://github.com/AI5GW/SIGLENT,
copyright (C) 2022 Sebastian (AI5GW) <sebastian@baltic-lab.com>
"""
class SDG1060X():
    def __init__(self, rm, address, internal_oscillator = True):
        """
        Initialize Siglent SDG 1062X instrument.

        Parameters
        ----------
        rm : pyvisa.ResourceManger
            PyVISA ResourceManger object.
        address : string
            VISA resource locator. Example: 'GPIB0::8::INSTR'
        internal_oscillator : bool, optional
            If True (default), the AWG will use its own internal oscillator and
            emit the 10 MHz signal on the 10 MHz in/out port. If False, the AWG
            will instead use an external clock (i.e. another AWG) connected to
            the 10 MHz in/out port.

        Returns
        -------
        None.

        """
        
        self.device = rm.open(address, query_delay=0.25)
        # increase timeout to 10s to allow large transfers
        self.device.timeout = 10000
        # set up clock source
        self.set_oscillator(internal_oscillator)
        
    def set_oscillator(self, internal):
        if internal:
            self.device.write("ROSC INT;ROSC 10MOUT,ON")
        else:
            self.device.write("ROSC EXT;ROSC 10MOUT,OFF")
            
    def set_waveform(self, waveform, channel, samplerate = 1e6, amp = 1.0, name = "Remote"):
        # Normalize to [-1, 1] with no offset
        waveform /= np.max(np.abs(waveform))
        # Scale to [-2^15, 2^15-1] and discretize to signed 16 bit int
        waveform = (0x7FFF * waveform).astype('int16')
        # Upload waveform to device
        self.device.write_binary_values(
            f'C1:WVDT WVNM,{name},FREQ,1.0,TYPE,8,AMPL,{amp},OFST,0.0,PHASE,0.0,WAVEDATA,',
            waveform, datatype='i', is_big_endian=False)
        # Load waveform on given channel
        self.device.write(f"C{channel}:ARWV NAME,{name};")
        self.device.write(f"C{channel}:SRATE MODE,TARB,VALUE,{int(samplerate)},INTER,LINE")
        
    def burst(self, channel, enabled, edge = "RISE", N = 1):
        """
        Set up burst mode.

        Parameters
        ----------
        channel : int
            1 or 2. Selects channel to act on.
        enabled : bool
            Whether burst mode should be enabled.
        edge : string, optional
            Sets the trigger mode. "RISE" or "FALL". The default is "RISE".
        N : int or string, optional
            Sets number of times the waveform should be repeated after the
            trigger. Accepts an int or "INF" for infinite. The default is 1.

        Returns
        -------
        None.

        """
        if enabled:
            self.device.write(
                f"C{channel}:BTWV STATE,ON,TSRS,EXT,EDGE,{edge},TIME,{N}"
            )
        else:
            self.device.write(f"C{channel}:BTWV STATE,OFF")

def seq_to_waveforms(seq, samplerate):
    """
    Decode 

    Parameters
    ----------
    seq : pandas.DataFrame
        DataFrame containing pulse sequence. Rows are read in order.
        Expected columns: time_us (float, time in microseconds),
        L (bool, laser enabled), I (bool, I enabled), Q (bool, Q enabled).
    samplerate : float/int
        Sample rate of the generated signal. This must match the sample rate of
        the AWG. 1s/samplerate should be much smaller than the shortest pulse.

    Returns
    -------
    L : Array of floats
        Decoded binary signal for modulating the laser.
    I : Array of floats
        Decoded binary signal for modulating the I channel.
    Q : Array of floats
        Decoded binary signal for modulating the Q channel.

    """
    # Convert samples/s to samples/us
    multiplier = samplerate / 1e6
    
    # Initialize arrays
    L = np.array([])
    I = np.array([])
    Q = np.array([])
    
    # Iterate over dataframe rows and fill up waveforms
    for row in seq.iterrows():
        # Generate high signal of appropriate length
        n = round(multiplier * row[1]["time_us"])
        filled = np.ones(n)
        
        # Append high or low signal depending on boolean value 
        L = np.append(L, filled * row[1]["L"])
        I = np.append(I, filled * row[1]["I"])
        Q = np.append(Q, filled * row[1]["Q"])
        
    return L, I, Q
    

def vis_sequence_proportional(seq):
    """
    Visualize pulse sequence dataframe.
    The x axis reflects the actual timescales of the sequence.
    
    Parameters
    ----------
    seq : pandasDataFrame
        DataFrame containing pulse sequence. Rows are read in order.
        Expected columns: time_us (float, time in microseconds),
        L (bool, laser enabled), I (bool, I enabled), Q (bool, Q enabled).

    Returns
    -------
    None.
    """
    # Decode sequence
    L, I, Q = seq_to_waveforms(seq, 100e6)
    ts = np.linspace(0, len(L)/100, len(L))
    plt.plot(ts, L + 2.4, label = "Laser")
    plt.fill_between(ts, L + 2.4, 2.4, alpha = 0.5)
    plt.plot(ts, I + 1.2, label = "I")
    plt.fill_between(ts, I + 1.2, 1.2, alpha = 0.5)
    plt.plot(ts, Q , label = "Q")
    plt.fill_between(ts, Q, 0, alpha = 0.5)
    plt.xlabel("Time (us)")
    plt.gca().set(yticklabels=[], yticks=[])
    plt.legend()
    return plt.show()


def vis_sequence_equidistant(seq):
    """
    Visualize sequence dataframe with equidistant steps.
    Useful for sequences with long wait periods.
    Step durations are drawn on the x axis.

    Parameters
    ----------
    seq : pandas.DataFrame
        DataFrame containing pulse sequence. Rows are read in order.
        Expected columns: time_us (float, time in microseconds),
        L (bool, laser enabled), I (bool, I enabled), Q (bool, Q enabled).

    Returns
    -------
    None.
    """
    # Get number of steps
    n = seq.shape[0]
    
    # Initialize arrays
    L = np.array([])
    I = np.array([])
    Q = np.array([])
    
    # Iterate over dataframe rows and fill up waveforms
    for row in seq.iterrows():
        # Generate high signal of appropriate length
        filled = np.ones(100)
        
        # Append high or low signal depending on boolean value 
        L = np.append(L, filled * row[1]["L"])
        I = np.append(I, filled * row[1]["I"])
        Q = np.append(Q, filled * row[1]["Q"])
        
    ts = np.linspace(0, len(L)/100, len(L))
    plt.grid(axis = 'x', visible = True, ls = '--')
    
    plt.plot(ts, L + 2.6, label = "Laser")
    plt.fill_between(ts, L + 2.6, 2.6, alpha = 0.5)
    plt.plot(ts, I + 1.4, label = "I")
    plt.fill_between(ts, I + 1.4, 1.4, alpha = 0.5)
    plt.plot(ts, Q + 0.2, label = "Q")
    plt.fill_between(ts, Q + 0.2, 0.2, alpha = 0.5)
    plt.gca().set(
        yticklabels=["Q", "I", "L"],
        yticks=[0.7, 1.9, 3.1],
        xticklabels=[],
        xticks = range(n + 1)
    )
    plt.ylim(0.1, 3.7)
    
    
    if n < 8:
        print("Horizontal branch entered")
        for (i, row) in enumerate(seq.iterrows()):
            print("inside for loop")
            t = row[1]["time_us"]
            plt.text(i + 0.5, -0.1, f"{t} us", ha = 'center')
    else:
        for (i, row) in enumerate(seq.iterrows()):
            t = row[1]["time_us"]
            plt.text(i + 0.5, 0.05, f"{t} us", ha = 'center',
                     rotation = 'vertical', va = 'top')
            
        
    return plt.show()
    return None