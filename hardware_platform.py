# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:56:53 2020

@author: simsh
"""
import math
#import numpy as np
from core import Core, compCore
from core_complex import CoreComplex, compCoreComplex

class HardwarePlatform:
    
    def __init__(self, totalCores, coresPerComplex, cacheSizeL3, assumedCache):
        
        self.totalCores=totalCores
        # assumes all clusters are identical
        # should have an error if this isn't an integer
        self.coresPerComplex = coresPerComplex
        if totalCores/coresPerComplex > totalCores//coresPerComplex:
            self.totalComplexes = totalCores//coresPerComplex + 1
        else:
            self.totalComplexes = totalCores//coresPerComplex
        #self.totalComplexes = math.ceil(totalCores/coresPerComplex)
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

def comparePlatforms(hw1: HardwarePlatform, hw2: HardwarePlatform):
    #self.totalCores = totalCores
    assert(hw1.totalCores is hw2.totalCores)
    #self.coresPerComplex = coresPerComplex
    assert(hw1.coresPerComplex is hw2.coresPerComplex)
    #self.totalComplexes = math.ceil(totalCores / coresPerComplex)
    print(hw1.totalComplexes)
    print(hw2.totalComplexes)
    assert(hw1.totalComplexes is hw2.totalComplexes)
    #self.perComplexL3 = cacheSizeL3
    assert(hw1.perComplexL3 is hw2.perComplexL3)

    assert(len(hw1.complexList) is len(hw2.complexList))
    for idx in range(len(hw1.complexList)):
        compCoreComplex(hw1.complexList[idx], hw2.complexList[idx])

    assert(len(hw1.coreList) is len(hw2.coreList))
    for idx in range(len(hw1.coreList)):
        compCore(hw1.coreList[idx], hw2.coreList[idx])
    #self.complexList = []
    #self.coreList = []

    #for c in range(0, self.totalComplexes):
    #    self.complexList.append(CoreComplex(c, cacheSizeL3))

    #for c in range(0, totalCores):
    #    complexID = math.floor(c / coresPerComplex)
    #    core = Core(c, complexID, assumedCache)
    #    self.coreList.append(core)
    #    self.complexList[complexID].coreList.append(core)

if __name__== "__main__":
     main()
