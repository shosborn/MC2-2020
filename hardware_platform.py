# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:56:53 2020

@author: simsh
"""

import numpy as np
from core import Core

class HardwarePlatform:
    
    def __init__(self, totalCores, coresPerComplex, cacheSizeL3, assumedCache):
        
        self.totalCores=totalCores
        # assumes all clusters are identical
        # should have an error if this isn't an integer
        self.coresPerComplex=coresPerComplex
        self.totalComplexes=totalCores/coresPerComplex
        # variables describing cache
        #self.cacheSizeL2=cacheSizeL2
        self.perComplexL3=cacheSizeL3
        
        self.complexList=[]
        self.coreList=[]
        
        for c in range (0, totalCores):
            complexID=np.floor(c/self.totalComplexes)
            self.coreList.append(Core(c, complexID, assumedCache))
