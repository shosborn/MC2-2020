# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 10:31:05 2020

@author: simsh
"""

# from taskCluster import TaskCluster
# from taskCluster import TaskCluster
from makePairs import MakePairsILP
from task import Task
from constants import Constants


class CritLevelSystem:


    def __init__(self, level, assumedCache):
        self.level = level
        #self.firstInSystem = numHigherCritTasks + 1

        self.thePairs = []
        self.timeToPair=0
        self.tasksThisLevel = []
        self.assumedCache=assumedCache


    def loadSystem(self, filename):
        header = True
        tasksThisLevel=self.tasksThisLevel
        with open(filename, "r") as f:
            for line in f:
                if header:
                    # first two columns give task id and period; don't need for now
                    headerArr = line.split(",")
                    numTasks = 1
                    cacheListAB = []
                    cacheListC = []
                    for column in range(2, len(headerArr)):
                        keyList = headerArr[column].split("-")
                        
                        sibling = int(keyList[0])
                        critLevel = keyList[1]
                        '''
                        if critLevel == "A":
                            critLevelInt= Constants.LEVEL_A
                        elif critLevel == "B":
                            critLevelInt= Constants.LEVEL_B
                        else:
                            critLevelInt= Constants.LEVEL_C
                        '''
                        cache = int(keyList[2])
                        # update total number of cache
                        numTasks = max(numTasks, sibling)
                        # update possible cache allocations
                        if (critLevel == "A" or critLevel == "B") and cache not in cacheListAB:
                            cacheListAB.append(cache)
                        if (critLevel == "C") and cache not in cacheListC:
                            cacheListC.append(cache)
                    header = False
                else:
                    arr = line.split(",")
                    taskID = int(arr[0])
                    print("taskID=", taskID)
                    period = relDeadline = int(arr[1])
                    newTask = Task(taskID, self.level, period, relDeadline)
                    for column in range(2, len(arr)):
                        # add cost to newTask.allCosts with the appropriate key
                        keyList = headerArr[column].split("-")
                        sibling = int(keyList[0])
                        critLevel = keyList[1]
                        if critLevel == "A":
                            critLevelInt= Constants.LEVEL_A
                        elif critLevel == "B":
                            critLevelInt= Constants.LEVEL_B
                        else:
                            critLevelInt= Constants.LEVEL_C
                        
                        cacheList = int(keyList[2])
                        thisCost=float(arr[column])*float(period)
                        newTask.allCosts[(sibling, critLevelInt, cacheList)] = thisCost
                    tasksThisLevel.append(newTask)

    def setPairsList(self):
        pairsILP = MakePairsILP(self)
        results = pairsILP.makePairs()
        self.thePairs = results[0]
        # do we want to track runtime?
        self.timeToPair = results[1]


    def assignToCores(self, alg, coreList):
        # to-do: implement a second method for period-aware worst-fit
        # should this change each core's list of tasks?
        # using 0-indexed cores
        if len(self.thePairs)==0:
            self.setPairsList

        thePairs=self.thePairs

        sortedPairs = sorted(thePairs, key=lambda x: x[2], reverse=True)

        # pair = (task1, task2, pairUtil)
        for pair in sortedPairs:
            bestCoreSoFar = -1
            utilOnBest = Constants.ASSUMED_MAX_CAPACITY
            task1=pair[0]
            task2=pair[1]
            pairCost=self.tasksThisLevel[task1].allCosts[(task2, self.level, self.assumedCache)]
            pairUtil=float(pairCost/self.tasksThisLevel[task1].period)

            #for c in coreList:
            for c in range(len(coreList)):
                #pairUtil=thePairs[0].allCosts[(thePairs[1], self.level, self.assumedCache)]
                newCoreUtil = coreList[c].utilOnCore[self.level] + pairUtil
                if newCoreUtil <= Constants.ASSUMED_MAX_CAPACITY and newCoreUtil <= utilOnBest:
                    bestCoreSoFar = c
                    utilOnBest = newCoreUtil
            # done looping through cores

            # add pair to core and update core contents
            if bestCoreSoFar == -1:
                # pair couldn't fit anywhere
                return False
            else:
                coreList[bestCoreSoFar].utilOnCore[self.level] = utilOnBest
                coreList[bestCoreSoFar].pairsOnCore[self.level].append(pair)
        # returns only if all pairs could be placed on a core
        # return pairsByCore
        return True
    
def main():
    
    from taskSystem import taskSystem
    from hardware_platform import HardwarePlatform
    #from crit_level import CritLevel
    #from constants import Constants
    
    totalCores=4
    coresPerComplex=4
    cacheSizeL3=2

    assumedCache=cacheSizeL3

    fileLevelA="levelA-v1.csv"
    platform=HardwarePlatform(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA)
    mySystem.levelA.loadSystem(fileLevelA)
    mySystem.levelA.setPairsList()
    
    mySystem.levelA.assignToCores(Constants.WORST_FIT, platform.coreList)
             
                
if __name__== "__main__":
     main()  




