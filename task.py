# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 16:53:35 2020

@author: simsh
"""

from constants import Constants

class Task:
    
    def __init__(self, ID, taskLevel, period, relDeadline):
        self.ID=ID
        self.period = period
        self.relDeadline = relDeadline
        self.allUtil = {}
        if taskLevel == Constants.LEVEL_C:
            self.currentSoloUtil=0
            self.currentThreadedCost = 0
            self.currentThreadedUtil = 0
        

        
    

        
        