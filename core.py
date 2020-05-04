# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:49:16 2020

@author: simsh
"""

class Core:
    
    def __init__(self, coreID, complexID):
        self.coreID=coreID
        self.complexID=complexID
        self.maxCapacity=1
        self.utilOnCore=0
        #first list is for level A, second is for B
        self.pairsOnCore=([],[])
        '''
        self.L2_A
        self.L2_B
        self.L2_AB
        self.L3_A
        self.L3_AB
        self.L3_B
        '''
        