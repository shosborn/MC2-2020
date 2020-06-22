# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 16:53:35 2020

@author: simsh
"""

from constants import Constants

class Task:
    
    def __init__(self, ID, taskLevel, period, relDeadline, wss):
        self.ID=ID
        self.period = period
        self.relDeadline = relDeadline
        self.allUtil = {}
        if taskLevel == Constants.LEVEL_C:
            self.currentSoloUtil=0
            self.currentThreadedCost = 0
            self.currentThreadedUtil = 0
        # wss is in MB
        # 2020 platform has ways of 1MB each
        # half-ways of 512 KB each.
        self.wss = wss

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