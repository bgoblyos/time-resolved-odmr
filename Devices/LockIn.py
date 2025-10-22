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

import pandas as pd
import struct

class SR830M():
    def __init__(self, rm, address):
        self.device = rm.open_resource(address)
        self.device.timeout = 100000

        self.bufferSize = 16383

        self.sensDF = pd.DataFrame(
            columns = ["i", "V", "Vstr", "I", "Istr"],
            data = [
                [0,  2.0e-09, "2 nV",   2.0e-15, "2 fA"   ],
                [1,  5.0e-09, "5 nV",   5.0e-15, "5 fA"   ],
                [2,  1.0e-08, "10 nV",  1.0e-14, "10 fA"  ],
                [3,  2.0e-08, "20 nV",  2.0e-14, "20 fA"  ],
                [4,  5.0e-08, "50 nV",  5.0e-14, "50 fA"  ],
                [5,  1.0e-07, "100 nV", 1.0e-13, "100 fA" ],
                [6,  2.0e-07, "200 nV", 2.0e-13, "200 fA" ],
                [7,  5.0e-07, "500 nV", 5.0e-13, "500 fA" ],
                [8,  1.0e-06, "1 uV",   1.0e-12, "1 pA"   ],
                [9,  2.0e-06, "2 uV",   2.0e-12, "2 pA"   ],
                [10, 5.0e-06, "5 uV",   5.0e-12, "5 pA"   ],
                [11, 1.0e-05, "10 uV",  1.0e-11, "10 pA"  ],
                [12, 2.0e-05, "20 uV",  2.0e-11, "20 pA"  ],
                [13, 5.0e-05, "50 uV",  5.0e-11, "50 pA"  ],
                [14, 1.0e-04, "100 uV", 1.0e-10, "100 pA" ],
                [15, 2.0e-04, "200 uV", 2.0e-10, "200 pA" ],
                [16, 5.0e-04, "500 uV", 5.0e-10, "500 pA" ],
                [17, 1.0e-03, "1 mV",   1.0e-09, "1 nA"   ],
                [18, 2.0e-03, "2 mV",   2.0e-09, "2 nA"   ],
                [19, 5.0e-03, "5 mV",   5.0e-09, "5 nA"   ],
                [20, 1.0e-02, "10 mV",  1.0e-08, "10 nA"  ],
                [21, 2.0e-02, "20 mV",  2.0e-08, "20 nA"  ],
                [22, 5.0e-02, "50 mV",  5.0e-08, "50 nA"  ],
                [23, 1.0e-01, "100 mV", 1.0e-07, "100 nA" ],
                [24, 2.0e-01, "200 mV", 2.0e-07, "200 nA" ],
                [25, 5.0e-01, "500 mV", 5.0e-07, "500 nA" ],
                [26, 1.0e+00, "1 V",    1.0e-06, "1 uA"   ]
            ]
        )
        
        self.tauDF = pd.DataFrame(
            columns = ["i", "t", "tstr"],
            data = [
                [0,  1.0e-05, "10 us"  ],
                [1,  3.0e-05, "30 us"  ],
                [2,  1.0e-04, "100 us" ],
                [3,  3.0e-04, "300 us" ],
                [4,  1.0e-03, "1 ms"   ],
                [5,  3.0e-03, "3 ms"   ],
                [6,  1.0e-02, "10 ms"  ],
                [7,  3.0e-02, "30 ms"  ],
                [8,  1.0e-01, "100 ms" ],
                [9,  3.0e-01, "300 ms" ],
                [10, 1.0e+00, "1 s"    ],
                [11, 3.0e+00, "3 s"    ],
                [12, 1.0e+01, "10 s"   ],
                [13, 3.0e+01, "30 s"   ],
                [14, 1.0e+02, "100 s"  ],
                [15, 3.0e+02, "300 s"  ],
                [16, 1.0e+03, "1 ks"   ],
                [17, 3.0e+03, "3 ks"   ],
                [18, 1.0e+04, "10 ks"  ],
                [19, 3.0e+04, "30 ks"  ]
            ]
        )

        self.srateDF = pd.DataFrame(
            columns = ["i", "srate", "sratestr"],
            data = [
                [0,  6.25e-02, "62.5 mHz" ],
                [1,  1.25e-01, "125 mHz"  ],
                [2,  2.5e-01,  "250 mHz"  ],
                [3,  5.0e-01,  "500 mHz"  ],
                [4,  1.0e+00,  "1 Hz"     ],
                [5,  2.0e+00,  "2 Hz"     ],
                [6,  4.0e+00,  "4 Hz"     ],
                [7,  8.0e+00,  "8 Hz"     ],
                [8,  1.6e+01,  "16 Hz"    ],
                [9,  3.2e+01,  "32 Hz"    ],
                [10, 6.4e+01,  "64 Hz"    ],
                [11, 1.28e+02, "128 Hz"   ],
                [12, 2.56e+02, "256 Hz"   ],
                [13, 5.12e+02, "512 Hz"   ],
                [14, None,     "Trigger"  ]
            ]
        )

    # Queries either X,Y,R,Theta,Ref or the 4 aux channels plus two display values
    def snap(self, aux = False):
        if aux:
            labels = ["AUX1", "AUX2", "AUX3", "AUX4", "DISP1", "DISP2"]
            data = self.device.query("SNAP? 5,6,7,8,10,11").split(',')
        else:
            labels = ["X", "Y", "R", "Theta", "Ref"]
            data = self.device.query("SNAP? 1,2,3,4,9").split(',')

        return {labels[i]: float(data[i]) for i in range(len(labels))}
    
    def readBinNum(self):
        res = self.device.query('SPTS?')
        return int(res)
    
    def queryBinary(self, param):
        # Increse timeout, otherwise the transfer takes too long
        oldTimeout = self.device.timeout
        self.device.timeout = 60000 # 1 minute
    
        self.device.write(param)
        response = self.device.read_raw()
    
        # Reset the timeout
        self.device.timeout = oldTimeout
    
        return response

    def queryBinaryFloat(self, param):
        response = self.queryBinary(param)
        entries = len(response) // 4
        data = struct.unpack(f"{entries}f", response)
        return list(data)
    
    def readBuffer(self, buffer, firstPoint = 0, numPoints = 0):
       bufferSize = self.readBinNum()

       if bufferSize == 0:
           #logging.warning("The lock-in buffer is empty, nothing could be retrieved.")
           return []

       if numPoints <= 0:
           numPoints = bufferSize - firstPoint

       if (firstPoint >= bufferSize) or (firstPoint < 0):
           #logging.warning(f"Starting index is out of bounds (requested index {firstPoint} from {bufferSize} elements)")
           return []

       if (firstPoint + numPoints) > bufferSize:
           #logging.info("Requested too many points, clamping it.")
           numPoints = bufferSize - firstPoint

       queryStr = f"TRCB ? {buffer}, {firstPoint}, {numPoints}"
       return self.queryBinaryFloat(queryStr)



