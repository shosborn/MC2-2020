# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 10:31:05 2020

@author: simsh
"""

from Task import Task
from taskCluster import TaskCluster
from makePairs import MakePairsILP

class CritLevelSystem:
    
    #index values for all costs
    SIBLING=task.SIBLING
    CRIT_LEVEL=task.CRIT_LEVEL
    L2_PORTIONS=task.L2_PORTIONS
    L3_PORTIONS=task.L3_PORTIONS
    
    '''
    cache portions=unrestricted is the initial assumption.
    Assumes that each task has full cache access.
    '''
    UNRESTRICTED=task.UNRESTRICTED
    
    def __init__(self, level, higherLevelTasks):
        
        self.level=level
        self.nTotal=higherLevelTasks
        self.firstInSystem=nTotal+1
        #will be used by makePairs
        #needs to include all tasks in system
        #not higher-level tasks, not pseudo-tasks
        self.systemTotal=0
        
        self.assumedL2=UNRESTRICTED
        self.assumedL3=UNRESTRICTED
        
    def setPairsList(self):
        pairsILP=MakePairsILP(self)
        results=pairsILP.makePairs()
        self.thePairs=results[0]
        #do we want to track runtime?
        self.timeToPair=results[1]
    

        
        
        
    def assignToClusters(self):
        #make sure setPairsList has run!
        thePairs=self.thePairs
        '''
        Assign pairs to cores using worst-fit (maximize remaining capacity)
        When doing level B, rememember to account for already-assigned level A tasks
        Should we use period-aware fitting?
        '''
        
        
    def testSystem(self):
    ''''
    task set-up can wait
    for now, assume each task has a dictionary allCosts with keys in format
    (sibling, critLevel, L2_Portions, L3_Portions)
    '''
   '''
    
    def addTaskRandom(self):
        #generate random values
        addTask(self)
        
    def addTask(self):
    
        
    def assignAllPairCostsRandom(self):
        
    def assignAllPairCosts(self):
    
        
    def addTaskAndUpdateCostsRandom(self):
        
    def addTaskAndUpdateCosts(self, period, relDeadline):
        newTaskID=self.nTotal+1
        newTask=task(newTaskID, self.level, period, relDeadline)
        #level C costs
        newTask.allCosts[(newTaskID, LEVEL_C, ALL_L2_CACHE, ALL_L3_CACHE)]=soloCosts[LEVEL_C]
        

        for i in range(firstTaskID, nTotal+1):
            newTask.allCosts[(i, LEVEL_C, ALL_L2_CACHE, ALL_L3_CACHE)]=value
            levelTasks[i].allCosts[(newTaskID, LEVEL_C, ALL_L2_CACHE, ALL_L3_CACHE)]=value
        
        #level B Costs
        
        #level A costs
        
    #save a system as csv for later use
    def saveSystem(self):
    
    #load system from csv
    def loadSystem(self):
'''
        

        

        
    
        
        