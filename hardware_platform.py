# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:56:53 2020

@author: simsh
"""

class HardwarePlatform:
    
    def __init__(self):
        self.totalCores=totalCores
        #assumes all clusters are identical
        self.coresPerComplex=coresPerComplex
        #variables describing cache
        self.cacheSizeL2=cacheSizeL2
        self.perComplexL3=perComplexL3
        #need more variables here: ways/sets/colors, refill time, etc.