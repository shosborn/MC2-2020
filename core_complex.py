# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:53:32 2020

@author: simsh
"""

#from core import Core

from core import compCore
from cluster import compCluster

class CoreComplex:
    
    def __init__(self, complexID,CacheSizeL3):
        self.complexID = complexID
        self.coreList = []
        self.cacheSize=CacheSizeL3
        self.clusterList = [] #one complex can host two cluster: one solo and one threaded (this can happen for at most one complex)

def compCoreComplex(cc1: CoreComplex, cc2: CoreComplex):
    assert(cc1.complexID is cc2.complexID)
    assert(len(cc1.coreList) is len(cc2.coreList))
    for idx in range(len(cc1.coreList)):
        compCore(cc1.coreList[idx], cc2.coreList[idx])
    assert(cc1.cacheSize is cc2.cacheSize)
    assert(len(cc1.clusterList) is len(cc2.clusterList))
    for idx in range(len(cc1.clusterList)):
        compCluster(cc1.clusterList[idx], cc2.clusterList[idx])