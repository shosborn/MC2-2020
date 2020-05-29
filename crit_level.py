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
from cluster import Cluster
import math


class CritLevelSystem:


    def __init__(self, level, assumedCache, upperCritLevel = None):
        self.level = level
        #self.firstInSystem = numHigherCritTasks + 1

        self.thePairs = []
        self.timeToPair = 0
        self.tasksThisLevel = []
        self.upperCritLevel = upperCritLevel #reference to immediate upper criticality level.
        self.assumedCache = assumedCache
        if level == Constants.LEVEL_C:
            self.soloTasks=[]
            self.threadedTasks=[]
            self.totalSoloUtil = 0
            self.totalThreadedUtil = 0
            self.threadedCores=[]
            self.soloCores=[]
            self.soloClusters=[]
            self.threadedClusters=[]


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

    #applies to crit levels A and B
    def setPairsList(self):
        pairsILP = MakePairsILP(self)
        results = pairsILP.makePairs()
        self.thePairs = results[0]
        # do we want to track runtime?
        self.timeToPair = results[1]

    #applies to crit levels A and B
    def assignToCores(self, alg, coreList):
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
        # returns only if all pairs could be placed on a core
        # return pairsByCore
        return True

    #applies to crit level C
    def decideThreaded(self):
        '''
        Decide which tasks should be threaded/ unthreaded.
        Recall from ECRTS '19 that the oblivious approach is not bad;
        Exact approach to partitioning doesn't make that much difference.

        In any cache, we need an assumed cache level to start.
        '''
        for thisTask in self.tasksThisLevel:
            soloCost=thisTask.allcosts.allCosts(thisTask.ID, self.level, self.assumedCache)
            thisTask.currentSoloUtil = soloCost/thisTask.period
            threadedCost=0
            for otherTask in self.tasksThisLevel:
                threadedCost=max(threadedCost,
                                 thisTask.allCosts(otherTask.ID, self.level, self.assumedCache))
            thisTask.currentThreadedCost=threadedCost
            thisTask.currentThreadedUtil=threadedCost/thisTask.period

            if soloCost>threadedCost/2 or threadedCost/thisTask.period>1:
                self.soloTasks.append(thisTask)
                self.totalSoloUtil = self.totalSoloUtil + thisTask.soloCost/thisTask.period
            else:
                self.threadedTasks.append(thisTask)
                self.totalThreadedUtil = self.totalThreadedUtil + thisTask.currentThreadedUtil

    #applies to level C only
    def divideCores(self, coreList, coresPerComplex):
        #determine cores needed for solos
        soloCapacity=0
        c = 0
        while soloCapacity < self.totalSoloUtil:
            soloCapacity = soloCapacity + 1-coreList[c].utilOnCore[Constants.LEVEL_C]
            self.soloCores.append(coreList[c])
            c +=1
            if c ==len(coreList):
                #can't do all the solo tasks; return failure
                return False

        #determine cores needed for threaded
        c = len(coreList)-1
        remainingCores = len(coreList)-len(self.soloCores)
        while threadedCapacity < self.totalThreadedUtil:
            threadedCapacity = threadedCapacity + 2*(1-coreList[c].utilOnCore[Constants.LEVEL_C])
            self.threadedCores.append(coreList[c])
            c -=1
            remainingCores -=1
            if remainingCores < 0:
                return False

        #allocate any leftover cores
        nextSoloCore=len(self.soloCores)
        nextThreadedCore=c
        while remainingCores > 0:
            if self.totalThreadedUtil/threadedCapacity < self.totalSoloUtil/soloCapacity:
                threadedCapacity = threadedCapacity + 2 * (Constants.ASSUMED_MAX_CAPACITY - coreList[nextThreadedCore].utilOnCore[Constants.LEVEL_C])
                self.threadedCores.append(coreList[nextThreadedCore])
                nextThreadedCore -= 1
            else:
                soloCapacity = soloCapacity + Constants.ASSUMED_MAX_CAPACITY - coreList[nextSoloCore].utilOnCore[Constants.LEVEL_C]
                self.soloCores.append(coreList[nextSoloCore])
                nextSoloCore += 1
            remainingCores -= 1

        #define the clusters
        #each cluster has a list of cores, list of tasks
        numSoloClusters=math.ceil(len(self.soloCores)/coresPerComplex)
        for i in range (numSoloClusters):
            clusterCores=[]
            for j in range(i*coresPerComplex, min((i+1)*coresPerComplex, len(self.soloCores))):
                clusterCores.append(coreList[j])
            thisCluster=Cluster(clusterCores, False)
            self.soloClusters.append(thisCluster)
        numThreadedClusters=math.ceil(len(self.threadedClusters)/coresPerComplex)
        for i in range (numThreadedClusters):
            clusterCores=[]
            for j in range(i*coresPerComplex, min(i+1)*coresPerComplex, len(self.threadedCores)):
                clusterCores.append(coreList[j])
            thisCluster=Cluster(clusterCores, True)
            self.threadedClusters.append(thisCluster)


    #applies to level C only
    def assignTasksToClusters(self):
        '''
        For each set of tasks:
        --sort by non-increasing util.
        --assign to clusters via worst-fit (most space remaining) + testAndAddTask
        --sort clusters by increasing space remaining
        --testAndAddTask until we find something that fits
        --if nothing fits, fail
        '''

        #solo tasks
        self.soloTasks.sort(key=lambda x:x.currentSoloUtil, reverse=True)
        for t in self.soloTasks:
            success=False
            self.soloClusters.sort(key=lambda x:x.remainingCapacity, reverse=False)
            for c in self.soloClusters:
                if c.testAndAddTask(t):
                    success=True
                    break #out of for c in self.soloClusters
            if not success:
                # task could not be placed; fail
                return False

        # threaded tasks
        self.threadedTasks.sort(key=lambda x: x.currentThreadedUtil, reverse=True)
        for t in self.threadedTasks:
            success = False
            self.threadedClusters.sort(key=lambda x: x.remainingCapacity, reverse=False)
            for c in self.threadedClusters:
                if c.testAndAddTask(t):
                    success = True
                    break  # out of for c in self.soloClusters
            if not success:
                # task could not be placed; fail
                return False
        # all tasks were successfully placed onto a cluster
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




