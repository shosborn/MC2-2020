# -*- coding: utf-8 -*-
"""
Created on Fri May  1 14:25:48 2020

@author: simsh
"""



from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem
from constants import Constants

class taskSystem:
    
    def __init__(self, totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA):
        self.platform = HardwarePlatform(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
        self.levelA = CritLevelSystem(Constants.LEVEL_A, assumedCache)
        self.levelB = CritLevelSystem(Constants.LEVEL_B, assumedCache)

        self.levels = []
        self.levels.extend([self.levelA,self.levelB])

    def printPairsByCore(self):
        coreList=self.platform.coreList
        for c in coreList:
            print(c.coreID)
            print("Level A")
            for p in c.pairsOnCore[Constants.LEVEL_A]:
                task1=p[0]
                task2=p[1]
                period=self.levelA.tasksThisLevel[task1].period
                cost=self.levelA.tasksThisLevel[task1].allCosts[(task2, Constants.LEVEL_A, c.assignedCache)]
                util=float(cost/period)
                print(task1, task2, util)
            print()
                # How do we know a task's level?
                # tasks are stored as critLevel.allTasks
                # do we want to be able to access tasks independently of their level?
                #util=self.levelA.allTasks[task1].allCosts[(task2, Constants.LEVEL_A, ]
                
        

def main():
    totalCores=4
    coresPerComplex=4
    cacheSizeL3=2

    assumedCache=cacheSizeL3

    fileLevelA="levelA-v1.csv"
    #tasksFromFile=True

    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA)
    mySystem.levelA.loadSystem(fileLevelA)
    #mySystem.levelA=CritLevelSystem(Constants.LEVEL_A, fileLevelA, assumedCache)
    mySystem.levelA.setPairsList()
    #pairsByCore=mySystem.levelA.assignToClusters(WORST_FIT)
    mySystem.levelA.assignToCores(Constants.WORST_FIT, mySystem.platform.coreList)
    mySystem.printPairsByCore()

    #where do I add in overheads?



if __name__== "__main__":
     main()