#!/usr/bin/env python
import sys
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from csv import DictReader
from copy import copy
from collections import defaultdict

# For main plots
#LINE_STYLE = ['k-.', 'b--o' , 'c:^'  , 'r:o'   , 'k:^']#    , 'r--s'   , 'r:s'    ]
#schednames = ['EDF', 'Prior', 'IPC', 'IO', 'Both']
#legendnames= ['UEDF', r'Prior MC$^2$', 'Man. IPC', 'Man. IO', 'Both']
LINE_STYLE = ['k-.',    'b--o',     'c:s']#,  'r--o',          'r--^',          'b--v',          'k:o',          'k:^',          'c:v'] # , 'r--s'   , 'r:s' ,    ]
schednames = ['NO_THREAD', 'THREAD_COURSE',    'THREAD_FINE']#,  'IO',           'IOHIGH',       'IOLOW',        'Both',         'BothHIGH',     'BothLOW']
legendnames= ['NO', 'CORE', 'THREAD']#['R|R',    'C|C',      'O|C',  'C|C+A/B-ALL',  'C|C+A/B-LP',   'C|C+A/B-SP',   'O|C+A/B-ALL',  'O|C+A/B-LP',   'O|C+A/B-SP']

# For main plots
#LINE_STYLE = ['k-.', 'b--o' ]#    , 'r--s'   , 'r:s'    ]
#schednames = ['Prior', 'IO']
#legendnames= [r'Prior MC$^2$', 'Man. IO']


# For LBA plots
#LINE_STYLE = ['c--^'   , 'c:^'    , 'r--s'   , 'r:s'    , 'm--D'       , 'm:D'        ]
#schednames = ['CBA-PST', 'CBA-RST', 'WBA-PST', 'WBA-RST', 'CBA-PST-OPT', 'CBA-RST-OPT']
#legendnames= ['CBA/PST', 'CBA/RST', 'WBA/PST', 'WBA/RST', 'LBA/PST'    , 'LBA/RST'    ]


def main():
    datadir = "results/"
    outdir = "plots/"
    total_time = 0
    total_count = 0
    fnum = 0
    donefiles = os.listdir(os.getcwd() + "/" + outdir + "pngs/")
    #filenames = ['light-light-heavy--harmonic-long--uni-heavy--uni-heavy--uni-medium--regular--uni-large--uni-light--fixed',         'medium-medium-medium--harmonic-long--uni-medium--uni-light--uni-heavy--way-heavy--uni-small--uni-heavy--fixed', 'medium-medium-medium--harmonic-long--uni-medium--uni-light--uni-medium--regular--uni-large--uni-light--fixed']
    #for filename in filenames:
    for filename in os.listdir(os.getcwd() + "/" + datadir):
        if filename + ".png" in donefiles:
            continue
        d = DictReader(open(datadir + filename, 'r'))
        data = defaultdict(list)
        for row in d:
            for key, value in row.iteritems():
                if key in schednames + ["SYS_UTIL"]:
                    data[key].append(float(value))
                else:
                    data[key].append(value)

        npdata = defaultdict(list)
        npdata["SYS_UTIL"] = np.asarray(data["SYS_UTIL"])
        idx_ord = npdata["SYS_UTIL"].argsort()

        for key in data.keys():
            npdata[key] = np.asarray(data[key])[idx_ord]

        plt.figure(figsize=(8,4))
        plt.ylabel("Schedulability")
        plt.xlabel("System Utilization")
        lw = 4.0
	schedset = []
	#if 'no_cam' in filename and 'net_none' in filename:
	#    LINE_STYLE = ['k-.', 'b--o']#, 'b:o'   , 'c:^'    , 'r--s'   , 'r:s'    ]
	#    schednames = ['EDF', 'Managed']
	#    legendnames= ['UEDF', 'OS-Isolated']
	#else:
	#    LINE_STYLE = ['k-.', 'b--o' , 'c:^'  ]#, 'b:o'   , 'c:^'    , 'r--s'   , 'r:s'    ]
	#    schednames = ['EDF', 'Managed', 'Unmanaged']
	#    legendnames= ['UEDF', 'OS-Isolated', r'Prior MC$^2$']
    
        for ndx, sched in enumerate(schednames):
            plt.plot(npdata["SYS_UTIL"], npdata[sched], LINE_STYLE[ndx], label=legendnames[ndx], linewidth=lw, markersize = lw*3)
            plt.xlim(0,int(max(npdata["SYS_UTIL"])+1))
            lw -= 0.3
        
        plt.legend(loc="upper right")
        plt.savefig(outdir + "pdfs/" + filename + ".pdf", bbox_inches='tight', pad_inches=0.1)
        plt.savefig(outdir + "pngs/" + filename + ".png", bbox_inches='tight', pad_inches=0.1)

        plt.close()

            
        #for ndx, count in enumerate(npdata['Count']):
        #    if count != None:
        #        total_count += int(count)
        
    #print 'count is ' + str(total_count)
        
if __name__ == '__main__':
    main()
