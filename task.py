# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 16:53:35 2020

@author: simsh
"""


class Task:
    
    def __init__(self, ID, taskLevel, period, relDeadline,wss=1):
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

        def __repr__(self):
            return "ID: %s"%self.ID

        def __srt__(self):
            return "ID: %s" % self.ID

        def __eq__(self, other):
            if isinstance(other, self.__class__):
                return self.ID == other.ID
            else:
                return False

        def __ne__(self, other):
            return not self.__eq__(other)

        
    

        
        