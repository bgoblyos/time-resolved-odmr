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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from Devices.Dummy import Dummy
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
        if address == "DUMMY":
            self.device = Dummy()
        else:
            self.device = rm.open_resource(address, query_delay=0.25)
            # increase timeout to 10s to allow large transfers
            self.device.timeout = 10000
            
        # set up clock source
        self.set_oscillator(internal_oscillator)
        
    def set_oscillator(self, internal):
        if internal:
            self.device.write("ROSC INT;ROSC 10MOUT,ON")
        else:
            self.device.write("ROSC EXT;ROSC 10MOUT,OFF")
            
    def output(self, channel, state = True, load = 50, polarity = "NOR"):
        """
        Set the output of the given channel.

        Parameters
        ----------
        channel : int
            Channel to act on. 1 or 2.
        state : bool, optional
            Sets whether to enable output. The default is True.
        load : int, optional
            Output impedance in Ohms. The default is 50.
        polarity : str, optional
            Output polarity. "NOR" is normal and "INVT" is inverted.
            The default is "NOR".

        Returns
        -------
        None.

        """
        
        cmd = (
            f"C{channel}:OUTP " +
            "ON," if state else "OFF," +
            f"LOAD,{load}," +
            f"PLRT,{polarity}"
        )
        self.device.write(cmd)
    def set_waveform(
            self,
            channel, 
            waveform,
            samplerate = 1e6,
            amp = 1.0,
            name = "Remote",
            offset = 0.0
    ):
        """
        Uploads and sets waveform to active.

        Parameters
        ----------
        channel : int
            Channel to act on. 1 or 2.
        waveform : array of floats
            Waveform to be displayed.
        samplerate : float, optional
            Samples per second. Affects how quickly the waveform is emitted.
            The default is 1e6.
        amp : float, optional
            Waveform amplitude in V. The default is 1.0.
        name : str, optional
            Waveform name. Used for saving the waveform and is displayed on the
            device. The default is "Remote".
        offset : float, optional
            Zero level offset in V. The default is 0.0.

        Returns
        -------
        waveform : array of int16
            Returns waveform as it was sent, including int16 stretching and
            lengthwise padding.

        """
        # Normalize to [-1, 1] with no offset
        factor = np.max(np.abs(waveform))
        if factor != 0:
            waveform /= factor
            
        # The AWG seems to only accept sequences that are 2^k-2 long,
        # so we need to pad the waveform to the nearest such length.
        
        # Store the length+2 for convenience
        n = len(waveform) + 2
        
        # If n is not a power of two, perform padding
        if n & (n-1) != 0:
            # Find target length (next smallest power of two)
            # Always send at least 2^16-2 points, otherwise the AWG won't work
            tgt = np.maximum(int(2**(np.ceil(np.log2(n)))), 0x10000)
            # Calculate remaining elements that need to be added. Note that we
            # use n here (which is len + 2), so the total length will be 2^k-2
            rem = tgt - n
            waveform = np.append(waveform, np.zeros(rem))
        
        # Scale to [-2^15, 2^15-1] and discretize to signed 16 bit int
        waveform = (0x7FFF * waveform).astype('int')
        
        # self.device.write_binary_values('C1:WVDT WVNM,remote,FREQ,1.0,TYPE,8,AMPL,1.0,OFST,0.0,PHASE,0.0,WAVEDATA,', waveform, datatype='i', is_big_endian=False)
        # self.device.write("C1:ARWV NAME,remote")
        # self.device.write("C1:SRATE MODE,TARB,VALUE,%f,INTER,LINE" % samplerate)
    
        # Upload waveform to device
        cmd = (
            f"C{channel}:WVDT " +
            f"WVNM,{name}," +
            "FREQ,1.0," +
            f"AMPL,{amp}," +
            f"OFST,{offset}," +
            "PHASE,0.0," +
            f"LENGTH,{2*len(waveform)}," + # This may not be necessary
            "WAVEDATA,"
        )
        self.device.write_binary_values(
            cmd, waveform, datatype='i', is_big_endian=False)
        
        # Load waveform on given channel
        self.device.write(f"C{channel}:ARWV NAME,{name}")
        self.device.write(
            f"C{channel}:SRATE MODE,TARB,VALUE,%f,INTER,LINE" % samplerate)
        
        return waveform
        
    def burst_off(self, channel):
        """
        Disable burst mode

        Parameters
        ----------
        channel : int
            1 or 2. Selects channel on which to disable burst mode.

        Returns
        -------
        None.
        """
        self.device.write(f"C{channel}:BTWV STATE,OFF")

    def burst_int(self,
                  channel,
                  period = 0.001,
                  delay = 0,
                  phase = 0,
                  n = 1,
                  trig_out = "RISE",
        ):
        """
        Enable burst mode with internal trigger.

        Parameters
        ----------
        channel : int
            Channel to act on. 1 or 2.
        period : float, optional
            Repetition period in seconds. The default is 0.001.
        delay : float, optional
            Trigger delay in seconds. The default is 0.
        phase : float, optional
            Starting phase in degrees. The default is 0.
        n : int or str, optional
            Number of waveforms to emit in each burst. Use 'INF' for
            continous signal. The default is 1.
        trig_out : str, optional
            When to emit trigger out. Valid options are "OFF", "RISE" and
            "FALL". The default is "RISE".

        Returns
        -------
        None.

        """
        
        cmd = (
            f"C{channel}:BTWV " +
            "STATE,ON," +
            "TRSR,INT," +
            f"PRD,{period}," +
            f"DLAY,{delay}," +
            f"TRMD,{trig_out}," +
            f"TIME,{n}"
        )
        
        self.device.write(cmd)

    def burst_ext(self,
                 channel,
                 delay = 0,
                 phase = 0,
                 n = 1,
                 edge = "RISE",
       ):
       """
       Enable burst mode with external trigger.

       Parameters
       ----------
       channel : int
           Channel to act on. 1 or 2.
       delay : float, optional
           Trigger delay in seconds. The default is 0.
       phase : float, optional
           Starting phase in degrees. The default is 0.
       n : int or str, optional
           Number of waveforms to emit in each burst. Use 'INF' for
           continous signal. The default is 1.
       edge : str, optional
           When to trigger burst mode. Valid options are "RISE" and "FALL".
           The default is "RISE".

       Returns
       -------
       None.

       """
       
       cmd = (
           f"C{channel}:BTWV " +
           "STATE,ON," +
           "TRSR,EXT," +
           f"DLAY,{delay}," +
           f"EDGE,{edge}," +
           f"TIME,{n}"
       )
       
       self.device.write(cmd)


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
    # Convert samples/s to samples/us. For some reason the AWG wants 4 times
    # as many points, otherwise the timescale is off.
    multiplier = 4 * samplerate / 1e6
    
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
