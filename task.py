# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 16:53:35 2020

@author: simsh
"""
        self.taskLevel=taskLevel

SPORADIC=0
PERIODIC=1

ANY_CORE=-1

'''
Tuples can be used as dictionary keys!
'''

#index values for tuples used as cost keys
SIBLING=0
CRIT_LEVEL=1
L2_PORTIONS=2
L3_PORTIONS=3

class Task:
    
    def __init__(self, ID, taskLevel, period, relDeadline):
        self.ID=ID
        self.period=period
        self.relDeadline=relDeadline
        self.allCosts={}
        #self.costA=costA
        #self.costB=costB
        #self.costC=costC
        self.wss=wss
        #self.allCostsA=[]
        #self.allCostsB=[]
        #self.allCostsC=[]
        

        
    

        
        