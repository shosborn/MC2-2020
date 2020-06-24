# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:56:53 2020

@author: simsh
"""
import math
#import numpy as np
from core import Core
from core_complex import CoreComplex

class HardwarePlatform:
    
    def __init__(self, totalCores, coresPerComplex, cacheSizeL3, assumedCache):
        
        self.totalCores=totalCores
        # assumes all clusters are identical
        # should have an error if this isn't an integer
        self.coresPerComplex = coresPerComplex
        self.totalComplexes = math.ceil(totalCores/coresPerComplex)
        #print(self.totalComplexes)
        # variables describing cache
        #self.cacheSizeL2=cacheSizeL2
        self.perComplexL3=cacheSizeL3
        
        self.complexList=[]
        self.coreList=[]

        for c in range(0,self.totalComplexes):
            self.complexList.append(CoreComplex(c,cacheSizeL3))
        
        for c in range (0, totalCores):
            complexID = math.floor(c/coresPerComplex)
            core = Core(c, complexID, assumedCache)
            self.coreList.append(core)
            self.complexList[complexID].coreList.append(core)

def main():
    h = HardwarePlatform(16,4,16,2)
    for comp in h.complexList:
        print("complex id: ", comp.complexID)
        for core in comp.coreList:
            print(core.coreID, end=" ")
        print()

if __name__== "__main__":
     main()
