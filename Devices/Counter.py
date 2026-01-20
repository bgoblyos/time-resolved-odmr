"""
Phase Matrix 25B frequency counter

Only used for develeopment, the device is not present in the student lab setup.
"""
class PM25B():
    def __init__(self, rm, addr, ):
        self.device = rm.open_resource(addr)
        self.device.read_termination = '\r'
        self.device.write("PA")
        self.device.write("BR")

    def read(self):
        "Take a frequency and power reading and return them in Hz and dBm respectively"
        resp = self.device.read()
        freq, power = [float(x.strip()) for x in resp.split(',')]
        return freq, power
