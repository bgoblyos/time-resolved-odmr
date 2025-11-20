# Copyright (C) 2025 Bence Göblyös

"""
pico-pulse sequence synthesizer
"""
class PicoPulse():
    def __init__(self, rm , addr):
        self.device = rm.open_resource(addr)

    def encodeSequence(self, seq, cycle = False, innerLoop = 0, outerLoop = None):
        cmd = ""
        if cycle:
            cmd += "CPULSE"
        else:
            cmd += "PULSE"

        # Set up inner loop
        m = round(innerLoop)
        if m < 0:
            m = 0

        cmd += f" {m}"

        # Set up outer loop
        if outerLoop is not None and outerLoop >= 0 and outerLoop <= (1 << 32 - 1):
            n = round(outerLoop)
        else:
            n = 1 << 32 - 1

        cmd += f" {n} "

        #TODO: Check if dataframe has all the columns we need

        for i in range(len(seq)):
            t = round(seq.time[i])
            t = t if t > 0 else 0

            out = 0
            if "ch1" in seq and seq.ch1[i] > 0:
                out += 1
            if "ch2" in seq and seq.ch2[i] > 0:
                out += 2
            if "ch3" in seq and seq.ch3[i] > 0:
                out += 4
            if "ch4" in seq and seq.ch4[i] > 0:
                out += 8
            if "ch5" in seq and seq.ch5[i] > 0:
                out += 16


            cmd += f"{t},{out},"

        return cmd

    def sendSequence(self, seq, **kwargs):
        cmd = self.encodeSequence(seq, **kwargs)
        res = self.device.query(cmd)
        return res
