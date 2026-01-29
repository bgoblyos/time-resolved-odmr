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

import numpy as np
import matplotlib.pyplot as plt
from Utilities.UnitFormatting import formatPrefix, getPrefix

def visSeqEquidistant(seq):
    """
    Visualize sequence dataframe with equidistant steps.
    Useful for sequences with long wait periods.
    Step durations are drawn on the x axis.

    Parameters
    ----------
    seq : pandas.DataFrame
        DataFrame containing pulse sequence. Rows are read in order.
        Expected columns: time (float, time in nanoseconds), "ch1" to "ch4" (int/bool).

    Returns
    -------
    plot.
    """
    # Get number of steps
    n = seq.shape[0]
    expand = 100
    
    data = {}
    
    for i in ["ch1", "ch2", "ch3", "ch4"]:
        if i in seq:
            data[i] = np.repeat(seq[i], expand)
        
    ts = np.linspace(0, n, n*expand)
    
    plt.grid(axis = 'x', visible = True, ls = '--')
    
    labels = []
    centers = []
    for i, ch in enumerate(data):
        offset = i*1.2 + 0.2
        centers.append(offset + 0.5)
        plt.plot(ts, data[ch] + offset, label = ch)
        plt.fill_between(ts, data[ch] + offset, offset, alpha = 0.5)
        labels.append(ch)
    
    plt.gca().set(
        yticks=centers,
        yticklabels=labels,
        xticklabels=[],
        xticks = range(n + 1)
    )
    plt.ylim(centers[0]-0.7, centers[-1]+0.7)
    
    
    if n < 8:
        for (i, row) in enumerate(seq.iterrows()):
            t = row[1]["time"]*1e-9
            plt.text(i + 0.5, -0.2, formatPrefix(t, "s"), ha = 'center')
    else:
        for (i, row) in enumerate(seq.iterrows()):
            t = row[1]["time"]*1e-9
            plt.text(i + 0.5, -0.05, formatPrefix(t, "s"), ha = 'center',
                     rotation = 'vertical', va = 'top')
            
        
    return plt.show()

def visSeqProportional(seq):
    expand = 1e-3
    
    data = {}

    for i in ["ch1", "ch2", "ch3", "ch4"]:
        if i in seq:
            data[i] = np.repeat(seq[i], np.round(seq.time*expand))
        
        
        
    t = np.sum(seq.time)
    factor, prefix = getPrefix(t*1e-9)
    ts = np.linspace(0, t*1e-9/factor, round(t*expand)) 
        
    labels = []
    centers = []
    for i, ch in enumerate(data):
        offset = i*1.2 + 0.2
        centers.append(offset + 0.5)
        plt.plot(ts, data[ch] + offset, label = ch)
        plt.fill_between(ts, data[ch] + offset, offset, alpha = 0.5)
        labels.append(ch)
    
    plt.gca().set(
        yticks=centers,
        yticklabels=labels,
        #xticklabels=[],
        #xticks = np.cumsum(seq.time)
        xlabel = f"Time ({prefix}s)"
    )
    
    plt.ylim(centers[0]-0.7, centers[-1]+0.7)
    
    return plt.show()