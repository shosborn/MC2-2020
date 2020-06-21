# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:49:16 2020

@author: simsh
"""

from constants import Constants

class Core:
    
    def __init__(self, coreID, complexID, assumedCache):
        self.coreID=coreID
        self.complexID=complexID
        self.maxCapacity = Constants.ASSUMED_MAX_CAPACITY
        # first element in list is level A
        # second is level B, + level B costs of A
        # third is level C + level C costs of B and A
        self.utilOnCore=[0, 0, 0]
        # first element will be list for level A,
        # second will be for B
        self.pairsOnCore=[[],[]]
        self.assignedCache=assumedCache

        self.cacheAB = [1,1] #L3 cache size (in no of half way) for two threads of this core,
        # if threads share cache then put half the size in both place
        #e.g., if both threads share 4 half ways of cache, then use [2,2]: equality constraint in ilp?
        self.cacheC = 2 #L3 cache size (in no of half way) for level C, same accross all cores

        self.minLevelAPeriod = None
        '''
        self.L2_A
        self.L2_B
        self.L2_AB
        self.L3_A
        self.L3_AB
        self.L3_B
        '''

    def getAssignedCache(self,criticalityLevel):
        #use assignedCache for now
        return self.cacheAB if criticalityLevel <= Constants.LEVEL_B else self.cacheC

    def getMinABCache(self):
        return min(self.cacheAB)

    def getMAxABCache(self):
        return max(self.cacheAB)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.coreID == other.coreID
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)