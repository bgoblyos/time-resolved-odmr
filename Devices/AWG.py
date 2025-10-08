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
class SDG1062X():
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
            self.device.write("ROSC INT")
            self.device.write("ROSC 10MOUT,ON")
        else:
            self.device.write("ROSC EXT")
            self.device.write("ROSC 10MOUT,OFF")
            
    def output(self, channel, state = True, load = "HiZ", polarity = "NOR"):
        """
        Set the output of the given channel.

        Parameters
        ----------
        channel : int
            Channel to act on. 1 or 2.
        state : bool, optional
            Sets whether to enable output. The default is True.
        load : int or str, optional
            Output impedance in Ohms or "HiZ". The default is "HiZ".
        polarity : str, optional
            Output polarity. "NOR" is normal and "INVT" is inverted.
            The default is "NOR".

        Returns
        -------
        None.

        """
        
        # TODO: do not change parameter if not explicitly specified
        
        cmd = (
            f"C{channel}:OUTP " +
            ("ON," if state else "OFF,") +
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
            # Always send at least 2^15-2 points, otherwise the AWG won't work
            tgt = np.maximum(int(2**(np.ceil(np.log2(n)))), 0x8000)
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
        
    
    def set_waveform_exact(
            self,
            channel,
            waveform,
            samplerate = 1e6,
            amp = 10.0,
            offset = 0.0,
            name = 'Remote'
        ):
        """
        Uploads and sets waveform to active. Only works with normalized
        waveforms that are exactly 32766 elements long.

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
        
        waveform = (0x7FFF * waveform).astype('int16')
        
        cmd = (
            f"C{channel}:WVDT " +
            f"WVNM,{name}," +
            "FREQ,1.0," +
            f"AMPL,{amp}," +
            f"OFST,{offset}," +
            "PHASE,0.0," +
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

# TODO: Adapt this to the new setup (two laser channels, common trigger)
class LIQ_SDG1062X():
    """
    Class for modulating a laser and driving an IQ modulator using two Siglent
    SDG 1062X arbitrary waveform generators.
    The 10 MHz in/out and AUX in/out ports should be connected between devices:
     AWG1       AWG2
    10 MHz <-> 10 MHz
     AUX   <->  AUX
    """
    def __init__(self, rm, addr1, addr2, delay = 3e-07):
        """
        INitialize LIQ modulator setup.

        Parameters
        ----------
        rm : pyvisa.ResourceManager
            PyVISA ResourceManager instance to use when
            connecting to instruments.
        addr1 : str
            VISA resource locator of the primary AWG. This device will provide
            the 10 MHz clock and will output the laser modulation signal on
            channel 1. A trigger signal will also be emitted on AUX each time
            the sequence starts.
        addr2 : str
            VISA resource locator of the secondary AWG. This device will use
            an external 10 MHz clock and output the I and Q signals on channels
            1 and 2 respectively. The sequences will be triggered externally
            from AUX.
        delay : float, optional
            Delay between sending out the trigger from the primary AWG and the
            start of the sequence. Used to compensate for delays between the
            two devices. Needs to be calibrated to the actual setup.
            The default is 3e-07.

        Returns
        -------
        None.

        """
        
        self.awg1 = SDG1062X(rm, addr1, internal_oscillator=True)
        self.awg2 = SDG1062X(rm, addr2, internal_oscillator=False)
        self.delay = delay
        
    def set_sequence(self,
                     seq,
                     amp = 10,
                     burst_period = 0.001
        ):
        """
        

        Parameters
        ----------
        seq : TYPE
            DESCRIPTION.
        samplerate : TYPE, optional
            DESCRIPTION. The default is 30e6.
        amp : TYPE, optional
            DESCRIPTION. The default is 10.
        burst_period : TYPE, optional
            DESCRIPTION. The default is 0.001.

        Returns
        -------
        None.

        """
        # TODO: Update docstring
        
        # Disable all output
        self.awg1.output(1, state = False)
        self.awg2.output(1, state = False)
        self.awg2.output(2, state = False)
        
        # Decode DataFrame into individual channels
        L, I, Q, samplerate = seq_to_waveforms(seq)
        
        # Upload L channel
        Lsent = self.awg1.set_waveform_exact(
            1, L, samplerate=samplerate, amp = amp, name = "L")
        # Set up burst mode on L channel
        self.awg1.burst_int(1, period = burst_period, delay=self.delay)
        
        # Upload I channel
        Isent = self.awg2.set_waveform_exact(
            1, I, samplerate=samplerate, amp = amp, name = "I")
        # Set up burst mode on I channel
        self.awg2.burst_ext(1)
        
        # Upload Q channel
        Qsent = self.awg2.set_waveform_exact(
            2, Q, samplerate=samplerate, amp = amp, name = "I")
        # Set up burst mode on I channel
        self.awg2.burst_ext(2)
        
        # Enable all outputs
        self.awg1.output(1, state = True, load = "HiZ")
        self.awg2.output(1, state = True, load = "HiZ")
        self.awg2.output(2, state = True, load = "HiZ")
        
        return Lsent, Isent, Qsent
        
    def enable(self):
        self.awg1.output(1, state = True, load = "HiZ")
        self.awg2.output(1, state = True, load = "HiZ")
        self.awg2.output(2, state = True, load = "HiZ")
        
    def disable(self):
        self.awg1.output(1, state = False)
        self.awg2.output(1, state = False)
        self.awg2.output(2, state = False)

def seq_to_waveforms(seq):
    # Set number of points. The ideal seems to be 2^15-2 = 32766
    # This will be downsampled to 16384 by the AWG, but sending that value to
    # begin with doesn't work.
    p =  0x7FFE
   
    # Fill all channels with zeros
    Lp = np.zeros(p)
    Ln = np.zeros(p)
    I = np.zeros(p)
    Q = np.zeros(p)
    
    i = 0
    for (index, row) in seq.iterrows():
        count = 2 * round(row["length"])
        newL = row["L"]
        newI = row["I"]
        newQ = row["Q"]
        for j in range(count):
            Lp[i] = newL
            Ln[i] = -newL
            I[i] = newI
            Q[i] = newQ
            i += 1
            # TODO: bounds checking
            
    return  Lp, Ln, I, Q
        
# def seq_to_waveforms(seq, lock_in_hz):
#     # TODO: Add docstring
    
#     # Set number of points. The ideal seems to be 2^15-2 = 32766
#     # This will be downsampled to 16384 by the AWG, but sending that value to
#     # begin with doesn't work.
#     p =  0x7FFE
    
#     # Calculate the minimum amount of time it takes produce p points with
#     # maximum sampling rate. The AWG will downsample the series by a factor of
#     # 2, so we have to divide the numbe of points accordingly
#     # Also stretch it out to fill out most of the lock-in period.
#     # Without this, the AWG will emit the RMS during downtimes, which is bad.
#     tmin = np.maximum(
#         (p/2)/30e6,
#         0.98*1/lock_in_hz
#     )

#     # Get how long each step in the sequence will take in seconds
#     ts = seq["time_us"].values * 1e-6
#     # Calculate the endpoint of each step in time
#     boundaries = np.cumsum(ts)

#     # Round up the time to Tmin, otherwise we need a sampling rate higher than
#     # 30 MSa/s, resulting in a stretched signal
#     t = np.maximum(boundaries[-1], tmin)
#     # Generate p equidistant points in the time interval
#     samples = np.linspace(0, t, p, endpoint = False) # Generate sample points
#     # Calculate the final sampling rate, accounting for downsampling
#     samplerate = (p/2)/t
    
#     # Display the temporal resolution. This might be moved to a return value.
#     timeres = t / (p/2)
#     #print(timeres)
#     if timeres > 1:
#         print(f"Temporal resolution: {timeres:.9g} s")
#     elif timeres > 1e-3:
#         print(f"Temporal resolution: {(timeres*1000):.9g} ms")
#     elif timeres > 1e-6:
#         print(f"Temporal resolution: {(timeres*1e6):.9g} us")
#     else:
#         print(f"Temporal resolution: {(timeres*1e9):.9g} ns")
    
#     # Fill all channels with zeros
#     Lp = np.zeros(p)
#     Ln = np.zeros(p)
#     I = np.zeros(p)
#     Q = np.zeros(p)

#     # Iterate over all sample points
#     for (i, sample) in enumerate(samples):
#        # Figure out which step the sample point falls under. This is done by
#        # finding the first region where the endpoint is greater than the
#        # sample. For instance, if the sample is 30us and we have 2 20us steps,
#        # Step #2 is chosen because 20 is not greater than 30, but 40 is.
#        region = np.where(boundaries > sample)[0]
#        # If the region isn't empty (which can happen if the time was rounded up
#        # and the last interval is unaccounted for), check which channels should
#        # be on and set their value to 1.
#        if len(region) > 0:
#            if seq["L"].values[region[0]]:
#                Lp[i] = 1.0
#                Ln[i] = -1.0
#            if seq["I"].values[region[0]]:
#                I[i] = 1.0
#            if seq["Q"].values[region[0]]:
#                Q[i] = 1.0
#        else:
#            # We can break out of the for loop because all subsequent sample 
#            # points will be in the padding region, which is already 0 filled.
#            break

#     return Lp, Ln, I, Q, samplerate

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
