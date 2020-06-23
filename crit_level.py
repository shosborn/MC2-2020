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
import distributions
import math
import random
from overheads import Overheads
from numpy import random
from typing import Dict, Tuple

#Use this to detect if we accidentally created an infinite loop
_MAX_TASKS = 1000

def _task_C_util(task: Task) -> float:
    return task.cost_per_cache_crit(Constants.MAX_HALF_WAYS, Constants.LEVEL_C)/task.period

def _fitTask(task: Task, goal_util_C: float):
    base_util_C = _task_C_util(task)
    deflation_factor = goal_util_C / base_util_C
    # we shouldn't have gotten here unless our task was too heavy
    assert (deflation_factor < 1)
    task.deflate(deflation_factor)

class CritLevelSystem:


    def __init__(self, level: int, assumedCache):
        self.level: int = level
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


    def _createTask(self, task_id: int, scenario: Dict[str, str]) -> Task:
        """
        We create a task that has information on how it runs individually, but not yet as a thread
        :param task_id:
        :param scenario:
        :return: the task
        """
        #compute baseline utilization assuming full cache
        util_dist_by_crit = Constants.TASK_UTIL[scenario['taskUtilDist']]
        util_dist = util_dist_by_crit[self.level]
        baseUtil = distributions.sample_unif_distribution(util_dist)

        #compute period
        period_dist_by_crit = Constants.PERIOD_DIST[scenario['periodDist']]
        period_dist = period_dist_by_crit[self.level]
        if self.level is Constants.LEVEL_C:
            period = distributions.sample_unif_int_distribution(period_dist)
        else:
            period = distributions.sample_choice(period_dist)
        #compute baseline cost from base util and period
        baseCost = baseUtil*period
        #implicit deadlines
        relDeadline = period

        #compute wss
        wss_mean, wss_std = Constants.WSS_DIST[scenario['wssDist']]
        wss = distributions.sample_normal_dist(wss_mean, wss_std)
        #shouldn't have negative wss, 0.5 is arbitrary for now
        wss = max([0.5, wss])

        #randomly choose task's sensitivity to cache
        cache_sense_dist = Constants.CACHE_SENSITIVITY[scenario['possCacheSensitivity']]
        cache_sense = distributions.sample_choice(cache_sense_dist)

        #choose how our cost scales at lower levels
        crit_sense_dist_by_crit = Constants.CRIT_SENSITIVITY[scenario['critSensitivity']]
        crit_scale_dict = {}
        prev_scale = 1.0
        for level in range(self.level, Constants.MAX_LEVEL):
            assert(0 < prev_scale <= 1.0)
            crit_sense_mean, crit_sense_std = crit_sense_dist_by_crit[level]
            tentative_scaling = max([0, distributions.sample_normal_dist(crit_sense_mean, crit_sense_std)])
            crit_scale_dict[level] = max([prev_scale, tentative_scaling])
            prev_scale = min([prev_scale, tentative_scaling])

        #return a basic task. Still need to produce any threading related data
        return Task(task_id, self.level, baseCost, period, relDeadline, wss, cache_sense, crit_scale_dict)

    def _generate_smt_costs_AB(self, smt_friendliness_mean: float,
                               smt_friendliness_std: float, smt_unfriendliness_chance: float):
        for task in self.tasksThisLevel:
            for sibling in self.tasksThisLevel:
                task.allUtil[sibling.ID] = {}
                if task is not sibling:
                    if distributions.sample_bernoulli(smt_unfriendliness_chance):
                        smt_friendliness = 10
                    else:
                        smt_friendliness = distributions.sample_normal_dist(smt_friendliness_mean,smt_friendliness_std)
                        smt_friendliness = max([smt_friendliness, 0.01])
                    for half_ways in range(Constants.MAX_HALF_WAYS+1):
                        task.allUtil[sibling.ID][half_ways] = {}
                        for level in range(self.level, Constants.MAX_LEVEL):
                            task.allUtil[sibling.ID][half_ways][level] = {}
                            for half_ways_sibling in range(Constants.MAX_HALF_WAYS - half_ways):
                                task.allUtil[sibling.ID][half_ways][level][half_ways_sibling] = \
                                    task.cost_per_cache_crit(half_ways, level) + \
                                    smt_friendliness* sibling.cost_per_cache_crit(half_ways_sibling, level)
                else:
                    for half_ways in range(Constants.MAX_HALF_WAYS//2+1):
                        task.allUtil[sibling.ID][half_ways] = {}
                        for level in range(self.level, Constants.MAX_LEVEL):
                            task.allUtil[sibling.ID][half_ways][level] = {}
                            task.allUtil[sibling.ID][half_ways][level][half_ways] = \
                                task.cost_per_cache_crit(2*half_ways, level)
        return

    def _generate_smt_costs_C(self, smt_friendliness_mean: float, smt_friendliness_std: float):
        for task in self.tasksThisLevel:
            smt_friendliness = distributions.sample_normal_dist(smt_friendliness_mean, smt_friendliness_std)
            smt_friendliness = max([smt_friendliness, 1.0])
            for sibling in self.tasksThisLevel:
                task.allUtil[sibling.ID] = {}
                if task is not sibling:
                    for half_ways in range(Constants.MAX_HALF_WAYS+1):
                        task.allUtil[sibling.ID][half_ways] = {}
                        for level in range(self.level, Constants.MAX_LEVEL):
                            task.allUtil[sibling.ID][half_ways][level] = {}
                            for half_ways_sibling in range(Constants.MAX_HALF_WAYS+1):
                                task.allUtil[sibling.ID][half_ways][level][half_ways_sibling] = \
                                    task.cost_per_cache_crit(half_ways, level)*smt_friendliness
                else:
                    for half_ways in range(Constants.MAX_HALF_WAYS//2+1):
                        task.allUtil[sibling.ID][half_ways] = {}
                        for level in range(self.level, Constants.MAX_LEVEL):
                            task.allUtil[sibling.ID][half_ways][level] = {}
                            task.allUtil[sibling.ID][half_ways][level][half_ways] = \
                                task.cost_per_cache_crit(2*half_ways, level)
        return

    def _generate_smt_costs(self, smt_dist: Dict[int, Tuple[float,float,float]]):
        if self.level is Constants.LEVEL_A:
            smt_mean, smt_std, smt_unfriendly = smt_dist[Constants.LEVEL_A]
            self._generate_smt_costs_AB(smt_mean, smt_std, smt_unfriendly)
        elif self.level is Constants.LEVEL_B:
            smt_mean, smt_std, smt_unfriendly = smt_dist[Constants.LEVEL_B]
            self._generate_smt_costs_AB(smt_mean, smt_std, smt_unfriendly)
        else:
            smt_mean, smt_std, _unused_smt = smt_dist[Constants.LEVEL_C]
            self._generate_smt_costs_C(smt_mean, smt_std)
        return

    def createTasks(self, scenario: Dict[str,str], targetUtil: float, startingID: int) -> int:

        # Change wss to be from 0 to 32 half-ways
        # expected value of wss to be on average 2 MB (each way is 1 MB)
        # Normal centered at 2 MB with standard deviation of 2 MB
        # truncate low end at 0
        # save results as MB
        # cache allocation possibilities in half-ways from 0-32
        
        #print('createTasks')
        assert(targetUtil > 0)
        assert(startingID > 0)

        thisLevelUtil=0
        taskID=startingID

        while thisLevelUtil < targetUtil:
            #beware of infinite loops
            assert(taskID - startingID < _MAX_TASKS)
            newTask = self._createTask(taskID, scenario)
            taskID += 1
            newTask_C_util = _task_C_util(newTask)
            if thisLevelUtil + newTask_C_util >= targetUtil:
                _fitTask(newTask, targetUtil - thisLevelUtil)
                self.tasksThisLevel.append(newTask)
                break
            else:
                thisLevelUtil += newTask_C_util
                self.tasksThisLevel.append(newTask)

        # done creating tasks

        #set up SMT costs
        smt_dist = Constants.SMT_EFFECTIVENESS_DIST[scenario['smtEffectDist']]
        self._generate_smt_costs(smt_dist)

        return taskID - startingID
                                

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
                    newTask = Task(taskID, self.level, period, relDeadline, 1)
                    newTask = Task(taskID, self.level, period*1000, relDeadline*1000, 1) # to test
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
                        newTask.allUtil[(sibling, critLevelInt, cacheList)] = thisUtil*0.5 #to test
                    tasksThisLevel.append(newTask)

        startingCacheSize = 3
        endingCacheSize = Constants.MAX_HALF_WAYS
        #some random data for higher cache sizes
        for task in tasksThisLevel:
            factor = random.uniform(0.1,0.5)
            factor /= 100
            for otherTask in tasksThisLevel:
                for cacheSize in range(startingCacheSize,endingCacheSize+1):
                    for level in range(self.level,Constants.LEVEL_C+1):
                        task.allUtil[(otherTask.ID,level,cacheSize)] = \
                            task.allUtil[(otherTask.ID,level,cacheSize-1)] * math.exp(-cacheSize*factor)

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
        firstTask=True
        for thisTask in self.tasksThisLevel:
            thisTask.currentSoloUtil=thisTask.allUtil[(thisTask.ID, self.level, self.assumedCache)]
            
            if firstTask:
                otherTask=self.tasksThisLevel[1]
                firstTask==False
            else:
                otherTask=self.tasksThisLevel[0]
            
            print()
            print("Printing level C task.")
            print("taskID=", thisTask.ID)
            print(thisTask.allUtil)
            
            threadedUtil=thisTask.allUtil[(otherTask.ID, self.level, self.assumedCache)]
            '''
            threadedUtil=0
            for otherTask in self.tasksThisLevel:
                threadedUtil=max(threadedUtil,
                                 thisTask.allUtil[(otherTask.ID, self.level, self.assumedCache)])
            '''
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

    def assignClustersToCoreComplex(self,complexList,corePerComplex):
        complexNo = 0
        sharedSoloCluster = None
        sharedThreadedCluster = None
        for cluster in self.soloClusters:
            if len(cluster.coresThisCluster) == corePerComplex:
                #single cluster in this complex
                complexList[complexNo].clusterList.append(cluster)
                complexList[complexNo].coreList = cluster.coresThisCluster
                complexNo += 1
            else:
                sharedSoloCluster = cluster
        for cluster in self.threadedClusters:
            if len(cluster.coresThisCluster) == corePerComplex:
                #single cluster in this complex
                complexList[complexNo].clusterList.append(cluster)
                complexList[complexNo].coreList = cluster.coresThisCluster
                complexNo += 1
            else:
                sharedThreadedCluster = cluster

        if sharedSoloCluster is not None and sharedThreadedCluster is not None:
            complexList[complexNo].clusterList.append(sharedSoloCluster)
            complexList[complexNo].clusterList.append(sharedThreadedCluster)
            complexList[complexNo].coreList.extend(sharedSoloCluster.coreThisCluster)
            complexList[complexNo].coreList.extend(sharedThreadedCluster.coreThisCluster)

    def assignClusterID(self):
        if self.level == Constants.LEVEL_C:
            id = 0
            for cluster in self.soloClusters:
                cluster.clusterID = id
                id += 1
            for cluster in self.threadedClusters:
                cluster.clusterID = id
                id += 1

    def printCoreAssignment(self,coreList):
        critLevel = self.level
        startingTaskID = self.tasksThisLevel[0].ID
        for c in range(len(coreList)):
            print("core: ",c)
            for pair in coreList[c].pairsOnCore[self.level]:
                print("<",self.tasksThisLevel[pair[0]-startingTaskID].ID,",",self.tasksThisLevel[pair[1]-startingTaskID].ID,">",end=" ")
            print(coreList[c].utilOnCore[self.level])

    def schedulabilityTest(self, coreList, allCritLevels, overHeads):
        # this method won't be used
        if Constants.OVERHEAD_ACCOUNT:
            return self.schedulabilityTestOverhead(coreList,allCritLevels, overHeads)
        else:
            return self.schedulabilityTestNoOverhead(coreList,allCritLevels)


    def schedulabilityTestOverhead(self,coreList,allCritLevels,overHeads):
        '''
        this method won't be used
        perform schedulability test at this criticality level
        :param coreList: List of cores
        :param allCritLevels: reference to a list of all criticality levels
        :return: true of false depending on schedulability
        '''
        taskCount = 0
        for critLevels in allCritLevels:
            taskCount += len(critLevels.tasksThisLevel)

        if self.level <= Constants.LEVEL_B:
            #store minimum period of level-A pairs of each core
            if self.level == Constants.LEVEL_A:
                for core in coreList:
                    startingTaskID = self.tasksThisLevel[0].ID
                    if len(self.thePairs) > 0:
                        core.minLevelAPeriod = 999999
                        for pair in core.pairsOnCore[self.level]:
                            core.minLevelAPeriod = min(core.minLevelAPeriod,self.tasksThisLevel[pair[0] - startingTaskID].period)

            inflatedUtils = overHeads.accountForOverhead(costLevel=self.level, taskCount=taskCount, coreList=coreList,
                                                            clusterList=None, allCriticalityLevels=allCritLevels,
                                                            dedicatedIRQ=Constants.IS_DEDICATED_IRQ, dedicatedIRQCore=coreList[0])
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
                    #additional utilization due to preemption of level-B tasks by level-A tasks
                    #consided for level-B analysis
                    if self.level == Constants.LEVEL_B and level == Constants.LEVEL_A:
                        extraUtil = overHeads.CPMDInflationLevelAB(costLevel=Constants.LEVEL_B, pairs=core.pairsOnCore[Constants.LEVEL_B],
                                                                   core=core,
                                                                   allCriticalityLevels=allCritLevels,
                                                                   dedicatedIRQ=False,isDedicatedIRQCore=False)
                        coreUtil += extraUtil
        else:
            allClusters = self.soloClusters + self.threadedClusters
            print("sched test level: ", self.level, " task count:", taskCount)
            inflatedUtils = overHeads.accountForOverhead(self.level, taskCount, coreList, allClusters, allCritLevels,
                                                         Constants.IS_DEDICATED_IRQ,dedicatedIRQCore=coreList[0])

            print(len(allClusters), len(self.soloClusters), len(self.threadedClusters))

            for cluster in allClusters:
                totalUtil = [0, 0, 0]
                numCore = len(cluster.coresThisCluster)
                for level in (Constants.LEVEL_A, Constants.LEVEL_B):
                    for core in cluster.coresThisCluster:
                        for pair in core.pairsOnCore[level]:
                            util = inflatedUtils[level][pair]
                            totalUtil[level] += util
                        if level == Constants.LEVEL_A:
                            # additional utilization due to preemption of level-B tasks by level-A tasks
                            # consided for level-C analysis
                            extraUtil = overHeads.CPMDInflationLevelAB(costLevel=Constants.LEVEL_C, #level-C analysis
                                                                       pairs=core.pairsOnCore[Constants.LEVEL_B], #level-B pairs
                                                                       core=core,
                                                                       allCriticalityLevels=allCritLevels,
                                                                       dedicatedIRQ=False, isDedicatedIRQCore=False)
                            totalUtil[level] += extraUtil


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
        this method won't be used
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