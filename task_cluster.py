# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 10:57:19 2020

@author: simsh
"""

import Task

class TaskCluster:
    def __init__(self):
        self.taskList=[]
        self.pseudoTaskList=[]
        self.inflatedTaskList=[]
        #coreList will give means to get data on higher-crit tasks on same cluster
        self.coreList=coreList
        self.level=level
        
    #add pseudo-tasks to account for non-cache overheads    
    def addPseudoTasks(self):
        
    #create/update inflated tasks to account for cache levels
    def updateInflatedTasks(self):
        
    def getHigherLevelTasks(self):
        #not sure if this really needs its own method; mostly here as a reminder to me
        
    def testCluster(self):