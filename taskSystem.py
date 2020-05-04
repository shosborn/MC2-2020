# -*- coding: utf-8 -*-
"""
Created on Fri May  1 14:25:48 2020

@author: simsh
"""

#system-wide constants
LEVEL_A=0
LEVEL_B=1
LEVEL_C=2

WORST_FIT=0
PERIOD_AWARE_WORST=1

from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem

class taskSystem:
    
    def __init__(self):
        self.platform=HardwarePlatform(totalCores, coresPerComplex, cacheSizeL2, cacheSizeL3)
        #create level A, including task generation
        self.systemLevelA=CritLevelSystem(LEVEL_A, generator)
        self.systemLevelA.setPairsList()
        self.systemLevelA.assignToClusters(WORST_FIT)
        