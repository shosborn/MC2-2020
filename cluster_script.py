# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 18:08:52 2020

"""

# Creates a series of slurm commands to run sched tests on research cluster.
# Not actually a part of the sched study.

from constants import Constants
import sys

customCoreCount = False

'''
customCoreCount = True
email="testEmail"
period="Many"
numCores="16"
'''

email = sys.argv[1]
period = sys.argv[2]
if len(sys.argv) > 3:
    numCores = sys.argv[3]
    customCoreCount=True

# sbatch -p general -N 1 --mem 32g -n 1 -c 24 -t 0:20:00 --mail-type=end --mail-user=shosborn@live.unc.edu --wrap="python3 sched_study.py --period Short --smt High"

# this is the variable part
baseCommand = "sbatch -p general -N 1 --mem 128g -n 1 -c 24 -t 48:00:00 --mail-type=end --mail-user="
baseCommand += email
baseCommand +=" --wrap=\"python3 sched_study.py --period "
baseCommand += period

# build up different arguments
# get each of the three criticality_util distributions and the three task_utils for each person

# make sure this is ordered by priority in Constants
critUtilList = Constants.CRITICALITY_UTIL_DIST.keys()
taskUtilList = Constants.TASK_UTIL.keys()
smtUtilList = Constants.SMT_EFFECTIVENESS_DIST.keys()

# make sure critUtilList is ordered by priority
for t in taskUtilList:
    for c in critUtilList:
        for s in smtUtilList:
        
            arg = " --crit "
            arg += c
            arg += " --util "
            arg += t
            arg += " --smt "
            arg += s
            if customCoreCount:
                arg +=" -- processors "
                arg += numCores
            arg += "\""
            fullCommand = baseCommand + arg
            print(fullCommand)
            print()
        

    
        
