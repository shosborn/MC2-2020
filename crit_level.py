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
from overheads import Overheads
from numpy import random


class CritLevelSystem:


    def __init__(self, level, assumedCache, upperCritLevels = None):
        self.level = level
        #self.firstInSystem = numHigherCritTasks + 1

        self.thePairs = []
        self.timeToPair = 0
        self.tasksThisLevel = []
        #self.upperCritLevels = upperCritLevels #reference to immediate upper criticality level.
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


    def createTasks(self, possiblePeriods, targetUtil, taskUtilDis, possibleCacheSensitivity, smtEffectDis, possibleWSS, critSensitivity, startingID):

        # WSS is in bytes
        # cache allocation possibilities in half-ways from 0-32
        thisLevelUtil=0
        cacheLevels=Constants.CACHE_LEVELS
        taskID=startingID

        while thisLevelUtil < targetUtil:
            # set utilization
            if taskUtilDis[0]=='U':
                newUtil=random.uniform(taskUtilDis[1], taskUtilDis[2])
            if taskUtilDis[0]=='N':
                newUtil=random.normal(taskUtilDis[1], taskUtilDis[2])
            if newUtil <= 0 :
                newUtil = 0.01
            if newUtil > 1:
                newUtil = 1
            
            # don't exceed the target
            if thisLevelUtil + newUtil > targetUtil:
                break
               
            # set period and relative deadline
            period=relDeadline=random.choice(possiblePeriods)
            # set crit level sensitivity
            # set WSS and cacheSensitivity
            wss=random.choice(possibleWSS)
            cacheSensitivity=random.choice(possibleCacheSensitivity)
            # create task
            newTask = Task(taskID, self.level, period, relDeadline, wss)
            # set solo costs for all crit levels and cache allocations
            for crit in range(self.level+1, Constants.LEVEL_C + 1):
                if crit==self.level:
                    fullCacheUtil=newUtil
                else:
                    fullCacheUtil=newUtil/(critSensitivity*(crit-self.level))
                for c in cacheLevels:
                    # using Josh's formula as of 6/19
                    # per Josh, formula may need some changes
                    if c >=wss:
                        thisUtil=fullCacheUtil
                    else:
                        denom=cacheSensitivity*(c+512 * 2**10)
                        mult=wss/denom
                        thisUtil=fullCacheUtil * mult
                newTask.allUtil[(taskID, crit, c)] = thisUtil
            self.tasksThisLevel.append(newTask)
            taskID +=1
        # done creating tasks
        lastID=taskID-1
        numTasks=lastID-startingID+1
        '''
        if self.level==Constants.LEVEL_A or self.level==Constants.LEVEL_B:
            for task in self.tasksThisLevel:
                baseUtil=task.allUtil[(task.ID, Constants.LEVEL_C, cacheLevels[len(cacheLevels)-1])]
        '''
        
        #set up SMT costs
        if self.level==Constants.LEVEL_C:
            for task in self.tasksThisLevel:
                # determine task's effectivenss
                if smtEffectDis[0]=='U':
                    smtEffect=newUtil=random.uniform(taskUtilDis[1], taskUtilDis[2])
                if smtEffectDis[0]=='N':
                    smtEffect=random.normal(taskUtilDis[1], taskUtilDis[2])
                # value < 1 don't make sense
                if smtEffect < 1:
                    smtEffect=1
                    
                # fill in remaining 
                for c in cacheLevels:
                    soloUtil=task.allUtil[(task.ID, Constants.LEVEL_C, c)]
                    for i in range(0, numTasks):
                        buddyID=self.tasksThisLevel[i].ID
                        task.allUtil[(buddyID, Constants.LEVEL_C), c] = soloUtil * smtEffect
                        
        if self.level==Constants.LEVEL_A or self.level==Constants.LEVEL_A:
            # determine pair's effectiveness
            for task1 in self.tasksThisLevel:
                for task2ID in range(task1.ID+1, lastID+1):
                    if random() < smtEffectDis[3]:
                        # don't use SMT
                        smtEffect=10
                    elif smtEffectDis[0]=='U':
                        smtEffect=newUtil=random.uniform(taskUtilDis[1], taskUtilDis[2])
                    elif smtEffectDis[0]=='N':
                        smtEffect=random.normal(taskUtilDis[1], taskUtilDis[2])
                    # negative values don't make sense
                    if smtEffect < 0:
                        smtEffect=0
                        # fill in remaining costs
                        for c in cacheLevels:
                            for crit in range(self.level, Constants.LEVEL_C + 1):
                                soloUtil=soloUtil=task1.allUtil[(task1.ID, crit, c)]
                                task1.allUtil[(task2ID, crit, c)]=soloUtil * smtEffect
                                task2=self.tasksThisLevel[task2ID-startingID]
                                task2.allUtil[(task1.ID, crit, c)]=soloUtil * smtEffect
                                
                    
                        
                
                
                    
                
            
        
            
            

    def loadSystem(self, filename):
        '''
        Create a set of tasks for the appropriate level by reading in csv file
        '''
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
                    #print("taskID=", taskID)
                    period = relDeadline = int(arr[1])
                    newTask = Task(taskID, self.level, period, relDeadline)
                    #newTask = Task(taskID, self.level, period*100, relDeadline*100)
                    for column in range(2, len(arr)):
                        # add util to newTask.allUtil with the appropriate key
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
                        thisUtil = float(arr[column])
                        newTask.allUtil[(sibling, critLevelInt, cacheList)] = thisUtil
                    tasksThisLevel.append(newTask)

    #applies to crit levels A and B
    def setPairsList(self):
        pairsILP = MakePairsILP(self)
        results = pairsILP.makePairs()
        self.thePairs = results[0]
        # do we want to track runtime?
        self.timeToPair = results[1]
        print("Printing thePairs")
        print(self.thePairs)

    #applies to crit levels A and B
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
        startingTaskID=self.tasksThisLevel[0].ID
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
            pairUtil=self.tasksThisLevel[task1-startingTaskID].allUtil[(task2, self.level, self.assumedCache)]

            #for c in coreList:
            for c in range(len(coreList)):
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
                    coreList[bestCoreSoFar].utilOnCore[critLevel] += self.tasksThisLevel[task1-startingTaskID].allUtil[(task2, critLevel, self.assumedCache)]
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
            thisTask.currentSoloUtil=thisTask.allUtil[(thisTask.ID, self.level, self.assumedCache)]
            threadedUtil=0
            for otherTask in self.tasksThisLevel:
                threadedUtil=max(threadedUtil,
                                 thisTask.allUtil[(otherTask.ID, self.level, self.assumedCache)])
            thisTask.currentThreadedUtil=threadedUtil

            if thisTask.currentSoloUtil<thisTask.currentThreadedUtil/2 or thisTask.currentThreadedUtil>=Constants.MAX_THREADED_UTIL:
                self.soloTasks.append(thisTask)
                self.totalSoloUtil = self.totalSoloUtil + thisTask.currentSoloUtil
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
        print("Prelim. solo cores:")
        for  core in self.soloCores:
            print(core.coreID, end=",")
        print()

        #determine cores needed for threaded
        threadedCapacity=0
        c = len(coreList)-1
        remainingCores = len(coreList)-len(self.soloCores)
        while threadedCapacity < self.totalThreadedUtil:
            threadedCapacity = threadedCapacity + 2*(1-coreList[c].utilOnCore[Constants.LEVEL_C])
            self.threadedCores.append(coreList[c])
            c -=1
            remainingCores -=1
            if remainingCores < 0:
                return False
        print("Prelim. threadedCores cores:")
        for core in self.threadedCores:
            print(core.coreID, end=",")
        print()

        #allocate any leftover cores
        nextSoloCore=len(self.soloCores)
        nextThreadedCore=c
        while remainingCores > 0:
            #if threadedCapacity>0:
#            print("threaded % used: ", self.totalThreadedUtil/threadedCapacity)
#            print("solo % used: ", self.totalSoloUtil/soloCapacity)
            if threadedCapacity==0:
                # no threads; everything should be solo
                self.soloCores.append(coreList[nextSoloCore])
                soloCapacity = soloCapacity + Constants.ASSUMED_MAX_CAPACITY - coreList[nextSoloCore].utilOnCore[Constants.LEVEL_C]
                nextSoloCore +=1
            elif soloCapacity==0:
                # no solos; everything should be threaded
                threadedCapacity = threadedCapacity + 2 * (Constants.ASSUMED_MAX_CAPACITY - coreList[nextThreadedCore].utilOnCore[Constants.LEVEL_C])
                self.threadedCores.append(coreList[nextThreadedCore])
                nextThreadedCore -= 1
            else:
                #some of each
                if self.totalThreadedUtil/threadedCapacity > self.totalSoloUtil/soloCapacity:
                    threadedCapacity = threadedCapacity + 2 * (Constants.ASSUMED_MAX_CAPACITY - coreList[nextThreadedCore].utilOnCore[Constants.LEVEL_C])
                    self.threadedCores.append(coreList[nextThreadedCore])
                    nextThreadedCore -= 1
                else:
                    soloCapacity = soloCapacity + Constants.ASSUMED_MAX_CAPACITY - coreList[nextSoloCore].utilOnCore[Constants.LEVEL_C]
                    self.soloCores.append(coreList[nextSoloCore])
                    nextSoloCore += 1
            remainingCores -=1
                
        #define the clusters
        #each cluster has a list of cores, list of tasks
        numSoloClusters=math.ceil(len(self.soloCores)/coresPerComplex)
        for i in range (numSoloClusters):
            clusterCores=[]
            for j in range(i*coresPerComplex, min((i+1)*coresPerComplex, len(self.soloCores))):
                clusterCores.append(coreList[j])
            thisCluster=Cluster(clusterCores, False)
            self.soloClusters.append(thisCluster)
            
            
        numThreadedClusters=math.ceil(len(self.threadedCores)/coresPerComplex)
        print("numThreadedClusters: ", numThreadedClusters)
        #sizeLastSoloCluster=len(self.soloClusters[numSoloClusters-1].clusterCores)
        # deal with odd-sized threaded cluster, if it exists
        j=len(self.soloCores)
        clusterCores=[]
        while j <len(coreList):
            clusterCores.append(coreList[j])
            if (j+1) % coresPerComplex==0:
                thisCluster=Cluster(clusterCores, True)
                self.threadedClusters.append(thisCluster)
                clusterCores=[]
            j+=1
            #print("j=", j)
            

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
            self.soloClusters.sort(key=lambda x:x.remainingCapacity, reverse=True)
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
            self.threadedClusters.sort(key=lambda x: x.remainingCapacity, reverse=True)
            for c in self.threadedClusters:
                if c.testAndAddTask(t):
                    success = True
                    break  # out of for c in self.soloClusters
            if not success:
                # task could not be placed; fail
                return False
        # all tasks were successfully placed onto a cluster
        return True



    def printCoreAssignment(self,coreList):
        critLevel = self.level
        startingTaskID = self.tasksThisLevel[0].ID
        for c in range(len(coreList)):
            print("core: ",c)
            for pair in coreList[c].pairsOnCore[self.level]:
                print("<",self.tasksThisLevel[pair[0]-startingTaskID].ID,",",self.tasksThisLevel[pair[1]-startingTaskID].ID,">",end=" ")
            print(coreList[c].utilOnCore[self.level])

    def schedulabilityTest(self, coreList, allCritLevels):
        if Constants.OVERHEAD_ACCOUNT:
            return self.schedulabilityTestOverhead(coreList,allCritLevels)
        else:
            return self.schedulabilityTestNoOverhead(coreList,allCritLevels)


    def schedulabilityTestOverhead(self,coreList,allCritLevels):
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


        if self.level <= Constants.LEVEL_B:
            inflatedUtils = overHeads.accountForOverhead(self.level, taskCount, coreList, None, allCritLevels,
                                                         Constants.IS_DEDICATED_IRQ)
            print("sched test level: ", self.level, " task count:", taskCount)
            for core in coreList:
                coreUtil = 0
                for level in range(Constants.LEVEL_A,self.level+1):
                    for pair in core.pairsOnCore[level]:
                        # todo: cost should be inflated cost after ohead accounting (done). assumedCache should be changed to the final allocated cache size
                        # determine util assuming execution at this level
                        #util = allCritLevels[level].tasksThisLevel[pair[0]].allCosts[(pair[1], self.level, self.assumedCache)]/self.tasksThisLevel[pair[1]].period
                        startingTaskID = allCritLevels[level].tasksThisLevel[0].ID
                        util = inflatedUtils[level][pair]
                        coreUtil += util
                        if coreUtil > 1:
                            return False
        else:
            allClusters = self.soloClusters + self.threadedClusters
            print("sched test level: ", self.level, " task count:", taskCount)
            inflatedUtils = overHeads.accountForOverhead(self.level, taskCount, coreList, allClusters, allCritLevels,
                                                         Constants.IS_DEDICATED_IRQ)

            print(len(allClusters), len(self.soloClusters), len(self.threadedClusters))

            for cluster in allClusters:
                totalUtil = [0, 0, 0]
                numCore = len(cluster.coresThisCluster)
                for level in range(Constants.LEVEL_A, Constants.LEVEL_B + 1):
                    for core in cluster.coresThisCluster:
                        for pair in core.pairsOnCore[level]:
                            util = inflatedUtils[level][pair]
                            totalUtil[level] += util


                sortedTask = sorted(cluster.taskList, key=lambda task: inflatedUtils[self.level][(task.ID,task.ID)], reverse=True)
                h = inflatedUtils[self.level][(sortedTask[0].ID,sortedTask[0].ID)]
                H, index = 0, 1
                for task in sortedTask:
                    util = inflatedUtils[self.level][(task.ID,task.ID)]
                    totalUtil[self.level] += util
                    if index <= numCore - 1:
                        H += util
                    index += 1

                if totalUtil[Constants.LEVEL_A] + totalUtil[Constants.LEVEL_B] + totalUtil[Constants.LEVEL_C] > numCore:
                    return False
                if totalUtil[Constants.LEVEL_A] + totalUtil[Constants.LEVEL_B] + (numCore-1)*h + H >= numCore:
                    return False
        return True

    def schedulabilityTestNoOverhead(self, coreList, allCritLevels):
        '''
        Schedulability test without accounting for overheads
        :param coreList:
        :param allCritLevels:
        :return:
        '''
        if self.level <= Constants.LEVEL_B:
            for core in coreList:
                coreUtil = 0
                for level in range(Constants.LEVEL_A,self.level+1):
                    for pair in core.pairsOnCore[level]:
                        # todo: cost should be inflated cost after ohead accounting (done). assumedCache should be changed to the final allocated cache size
                        # determine util assuming execution at this level
                        #util = allCritLevels[level].tasksThisLevel[pair[0]].allCosts[(pair[1], self.level, self.assumedCache)]/self.tasksThisLevel[pair[1]].period
                        startingTaskID = allCritLevels[level].tasksThisLevel[0].ID
                        cacheSize = core.getAssignedCache(level)
                        util = allCritLevels[level].tasksThisLevel[pair[0]-startingTaskID].allUtil[(pair[1], self.level, cacheSize)]
                        coreUtil += util
                        if coreUtil > 1:
                            return False
        else:
            allClusters = self.soloClusters + self.threadedClusters
            for cluster in allClusters:
                if not cluster.schedTestNoOverheads():
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
    fileLevelC="levelC-v1.csv"
    platform=HardwarePlatform(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA,fileLevelB,fileLevelC)
    mySystem.levelA.loadSystem(fileLevelA)
    mySystem.levelA.setPairsList()
    
    print(mySystem.levelA.assignToCores(Constants.WORST_FIT, platform.coreList))

    mySystem.levelB.loadSystem(fileLevelB)
    mySystem.levelB.setPairsList()
    print(mySystem.levelB.assignToCores(Constants.WORST_FIT, platform.coreList))

    mySystem.levelA.printCoreAssignment(platform.coreList)
    #mySystem.levelB.printCoreAssignment(platform.coreList)

    #schedA = mySystem.levelA.schedulabilityTest(platform.coreList,mySystem.levels)
    schedB = mySystem.levelB.schedulabilityTest(platform.coreList,mySystem.levels)
    print(schedB)

if __name__== "__main__":
     main()