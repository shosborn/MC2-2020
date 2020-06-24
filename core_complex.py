# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:53:32 2020

@author: simsh
"""

#from core import Core

class CoreComplex:
    
    def __init__(self, complexID,CacheSizeL3):
        self.complexID = complexID
        self.coreList = []
        self.cacheSize=CacheSizeL3
        self.clusterList = [] #one complex can host two cluster: one solo and one threaded (this can happen for at most one complex)
        