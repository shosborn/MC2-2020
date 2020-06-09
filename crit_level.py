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
from overheads import Overheads


class CritLevelSystem:


    def __init__(self, level, assumedCache, upperCritLevels = None):
        self.level = level
        #self.firstInSystem = numHigherCritTasks + 1

        self.thePairs = []
        self.timeToPair = 0
        self.tasksThisLevel = []
        #self.upperCritLevels = upperCritLevels #reference to immediate upper criticality level.
        self.assumedCache = assumedCache


    def loadSystem(self, filename):
        header = True
        tasksThisLevel = self.tasksThisLevel
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
                        # to-do: the following codes are not required later. headerArr is used instead. Should they be removed?
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
                            critLevelInt = Constants.LEVEL_A
                        elif critLevel == "B":
                            critLevelInt = Constants.LEVEL_B
                        else:
                            critLevelInt = Constants.LEVEL_C
                        
                        cacheList = int(keyList[2])
                        thisCost = float(arr[column])*float(period)
                        newTask.allCosts[(sibling, critLevelInt, cacheList)] = thisCost
                    tasksThisLevel.append(newTask)

    def setPairsList(self):
        pairsILP = MakePairsILP(self)
        results = pairsILP.makePairs()
        self.thePairs = results[0]
        # do we want to track runtime?
        self.timeToPair = results[1]


    def assignToCores(self, alg, coreList):
        '''
        Assign tasks to cores, applicable to level-A and -B tasks
        :param alg: partitioning algorithm, unused
        :param coreList: list of cores
        :return:
        '''
        # to-do: implement a second method for period-aware worst-fit
        # should this change each core's list of tasks?
        # using 0-indexed cores
        if len(self.thePairs) == 0:
            raise NotImplementedError

        thePairs = self.thePairs

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
                #update lower levels utilizations upto level B on this core (can be done upto C, but may impact C's code), will be starting point for level B
                for critLevel in range(self.level+1,Constants.LEVEL_B+1):
                    coreList[bestCoreSoFar].utilOnCore[critLevel] += float(self.tasksThisLevel[task1].allCosts[(task2, critLevel, self.assumedCache)]/self.tasksThisLevel[task1].period)
        # returns only if all pairs could be placed on a core
        # return pairsByCore
        return True

    def printCoreAssignment(self,coreList):
        critLevel = self.level
        for c in range(len(coreList)):
            print("core: ",c)
            for pair in coreList[c].pairsOnCore[self.level]:
                print("<",self.tasksThisLevel[pair[0]].ID,",",self.tasksThisLevel[pair[1]].ID,">",end=" ")
            print(coreList[c].utilOnCore[self.level])

    def schedulabilityTest(self,coreList,allCritLevels):
        '''
        perform schedulability test at this criticality level
        :param coreList: List of cores
        :param allCritLevels: reference to a list of all criticality levels
        :return: true of false depending on schedulability
        '''
        taskCount = 0
        for critLevels in allCritLevels:
            taskCount += len(critLevels.tasksThisLevel)
        overHeads = Overheads()
        overHeads.loadOverheadData('oheads')
        inflatedPairs = overHeads.accountForOverhead(self.level, taskCount, coreList, allCritLevels)
        if self.level <= Constants.LEVEL_B:
            # inflatedPairs has pair -> (period,deadline,cost)
            for core in coreList:
                coreUtil = 0
                for level in range(Constants.LEVEL_A,self.level+1):
                    print("level: ",level)
                    for pair in core.pairsOnCore[level]:
                        # todo: cost should be inflated cost after ohead accounting (done). assumedCache should be changed to the final allocated cache size
                        # determine util assuming execution at this level
                        #util = allCritLevels[level].tasksThisLevel[pair[0]].allCosts[(pair[1], self.level, self.assumedCache)]/self.tasksThisLevel[pair[1]].period
                        print(pair)
                        util = inflatedPairs[level][pair][2]/inflatedPairs[level][pair][0]
                        print(util)
                        coreUtil += util
                        if coreUtil > 1:
                            return False
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
    fileLevelB="levelB-v1.csv"
    platform=HardwarePlatform(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA)
    mySystem.levelA.loadSystem(fileLevelA)
    mySystem.levelA.setPairsList()
    
    print(mySystem.levelA.assignToCores(Constants.WORST_FIT, platform.coreList))

    mySystem.levelB.loadSystem(fileLevelB)
    mySystem.levelB.setPairsList()
    print(mySystem.levelB.assignToCores(Constants.WORST_FIT, platform.coreList))

    #mySystem.levelA.printCoreAssignment(platform.coreList)
    #mySystem.levelB.printCoreAssignment(platform.coreList)

    schedA = mySystem.levelA.schedulabilityTest(platform.coreList,mySystem.levels)
    schedB = mySystem.levelB.schedulabilityTest(platform.coreList,mySystem.levels)
    print(schedA, schedB)

if __name__== "__main__":
     main()