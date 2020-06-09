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
        self.utilOnCore=[0, 0]
        # first element will be list for level A,
        # second will be for B
        self.pairsOnCore=[[],[]]
        self.assignedCache=assumedCache
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
        return self.assignedCache