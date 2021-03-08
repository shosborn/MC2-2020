# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 10:31:05 2020

@author: simsh
"""

# from taskCluster import TaskCluster
# from taskCluster import TaskCluster
from makePairs import MakePairsILP
from task import Task, get_pair_util
from constants import Constants
from cluster import Cluster
import distributions
from gurobipy import *
#import math
#import random
#from overheads import Overheads
#import numpy as np
from typing import Dict, Tuple

from core import compCore
from cluster import compCluster

#Use this to detect if we accidentally created an infinite loop
_MAX_TASKS = 1000

def _task_C_util(task: Task) -> float:
    return task.cost_per_cache_crit(Constants.MAX_HALF_WAYS, Constants.LEVEL_C)/task.period

def _task_A_util(task: Task) -> float:
    return task.cost_per_cache_crit(Constants.MAX_HALF_WAYS, Constants.LEVEL_A)/task.period

def _fitTask(task: Task, goal_util_A: float) -> None:
    base_util_A = _task_A_util(task)
    deflation_factor = goal_util_A / base_util_A
    # we shouldn't have gotten here unless our task was too heavy
    assert (deflation_factor < 1)
    task.deflate(deflation_factor)

class CritLevelSystem:
    def __init__(self, level: int, assumedCache: int):
        self.level: int = level
        #self.firstInSystem = numHigherCritTasks + 1

        self.thePairs = []
        self.timeToPair = 0
        self.tasksThisLevel = []

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
            self.sharedSoloCluster = None
            self.sharedThreadedCluster = None

    def getTask(self, task_id: int) -> Task:
        task_idx = task_id - self.tasksThisLevel[0].ID
        assert(0 <= task_idx < len(self.tasksThisLevel))
        return self.tasksThisLevel[task_idx]

    def _createTask(self, task_id: int, scenario: Dict[str, str], startingID: int, totUtil: float) -> Task:
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
        #shouldn't have negative wss, minimum of 32KB is informed by data
        wss = max([0.001*32, wss])

        #randomly choose task's sensitivity to cache
        cache_sense_dist = Constants.CACHE_SENSITIVITY[scenario['possCacheSensitivity']]
        cache_sense = distributions.sample_choice(cache_sense_dist)

        #choose how our cost scales at lower levels
        #crit_sense_dist_by_crit = Constants.CRIT_SENSITIVITY[scenario['critSensitivity']]
        #crit_scale_dict = {}
        #Lowering criticality level should not increase costs. Prevent this by reducing to how cost decreased
        #   with respect to the previous criticality level
        #prev_scale = 1.0
        #for level in range(Constants.LEVEL_A, Constants.MAX_LEVEL):
        #    assert(0 < prev_scale <= 1.0)
            #crit_sense_mean, crit_sense_std, crit_sense_min = crit_sense_dist_by_crit[level]
        #    tentative_scaling = max([crit_sense_min, distributions.sample_normal_dist(crit_sense_mean, crit_sense_std)])
        #    crit_scale_dict[level] = min([prev_scale, tentative_scaling])
        #    prev_scale = min([prev_scale, tentative_scaling])

        #return a basic task. Still need to produce any threading related data
        return Task(task_id, self.level, baseCost, period, relDeadline, wss, cache_sense, startingID, totUtil)

    def _generate_smt_costs_AB(self, smt_friendliness_mean: float,
                               smt_friendliness_std: float, smt_unfriendliness_chance: float) -> None:
        for task in self.tasksThisLevel:
            task.initialize_smt_array_AB(len(self.tasksThisLevel))
            for sibling in self.tasksThisLevel:
                if task is sibling:
                    #SMT irrelevant here
                    continue
                #task.allUtil_AB[sibling.ID] = {}
                if distributions.sample_bernoulli(smt_unfriendliness_chance):
                    smt_friendliness = 10 #punish for SMT
                else:
                    smt_friendliness = distributions.sample_normal_dist(smt_friendliness_mean,smt_friendliness_std)
                    smt_friendliness = max([smt_friendliness, 0.01])
                #For threaded tasks, do to color separation, I am only entitled to at most half the half-ways
                for half_ways in range(Constants.MAX_HALF_WAYS//2+1):
                    #task.allUtil_AB[sibling.ID][half_ways] = {}
                    for level in range(self.level, Constants.MAX_LEVEL):
                        #task.allUtil_AB[sibling.ID][half_ways][level] = {}
                        #The sibling task is limited to half the half-ways for the same reason
                        #for half_ways_sibling in range(Constants.MAX_HALF_WAYS//2+1):
                        #    #Use the individual costs and SMT friendliness to compute an SMT cost
                        #    util = task.cost_per_cache_crit(half_ways, level) + \
                        #           smt_friendliness*sibling.cost_per_cache_crit(half_ways_sibling, level)
                        #    util /= task.period
                        #    task.set_smt_util_AB(sibling.ID, half_ways, level, half_ways_sibling, util)
                        #    #task.allUtil_AB[sibling.ID,half_ways,level,half_ways_sibling] = \
                        #    #    task.cost_per_cache_crit(half_ways, level) + \
                        #    #    smt_friendliness* sibling.cost_per_cache_crit(half_ways_sibling, level)
                        #    #task.allUtil_AB[sibling.ID,half_ways,level,half_ways_sibling] /= task.period
                        util = task.cost_per_cache_crit(half_ways, level) + \
                            smt_friendliness*sibling.cost_per_cache_crit(half_ways, level)
                        util /= task.period
                        task.set_smt_util_AB(sibling.ID, half_ways, level, half_ways, util)
        return

    def _generate_smt_costs_AB_case_study(self, smt_friendliness_mean: float,
                               smt_friendliness_std: float, smt_unfriendliness_chance: float, dataset: str) -> None:
        for task in self.tasksThisLevel:
            task.initialize_smt_array_AB(len(self.tasksThisLevel))
            for sibling in self.tasksThisLevel:
                if task is sibling:
                    #SMT irrelevant here
                    continue
                #task.allUtil_AB[sibling.ID] = {}
                #print(dataset, task.name, sibling.name)
                smt_friendliness = Constants.SMT_EFFECTIVENESS_AB_CASE_STUDY[dataset][task.name][sibling.name]
                smt_friendliness = max([smt_friendliness, 0.01])
                '''if distributions.sample_bernoulli(smt_unfriendliness_chance):
                    smt_friendliness = 10 #punish for SMT
                else:
                    smt_friendliness = distributions.sample_normal_dist(smt_friendliness_mean,smt_friendliness_std)
                    smt_friendliness = max([smt_friendliness, 0.01])'''
                #For threaded tasks, do to color separation, I am only entitled to at most half the half-ways
                for half_ways in range(Constants.MAX_HALF_WAYS//2+1):
                    #task.allUtil_AB[sibling.ID][half_ways] = {}
                    for level in range(self.level, Constants.MAX_LEVEL):
                        #task.allUtil_AB[sibling.ID][half_ways][level] = {}
                        #The sibling task is limited to half the half-ways for the same reason
                        #for half_ways_sibling in range(Constants.MAX_HALF_WAYS//2+1):
                        #    #Use the individual costs and SMT friendliness to compute an SMT cost
                        #    util = task.cost_per_cache_crit(half_ways, level) + \
                        #           smt_friendliness*sibling.cost_per_cache_crit(half_ways_sibling, level)
                        #    util /= task.period
                        #    task.set_smt_util_AB(sibling.ID, half_ways, level, half_ways_sibling, util)
                        #    #task.allUtil_AB[sibling.ID,half_ways,level,half_ways_sibling] = \
                        #    #    task.cost_per_cache_crit(half_ways, level) + \
                        #    #    smt_friendliness* sibling.cost_per_cache_crit(half_ways_sibling, level)
                        #    #task.allUtil_AB[sibling.ID,half_ways,level,half_ways_sibling] /= task.period
                        #util = task.cost_per_cache_crit(half_ways, level) + \
                        #    smt_friendliness*sibling.cost_per_cache_crit(half_ways, level)
                        util = max(task.cost_per_cache_crit(half_ways, level),sibling.cost_per_cache_crit(half_ways, level)) + \
                               smt_friendliness*min(task.cost_per_cache_crit(half_ways, level),sibling.cost_per_cache_crit(half_ways, level))
                        util /= task.period
                        task.set_smt_util_AB(sibling.ID, half_ways, level, half_ways, util)
        return


    def _generate_smt_costs_C(self, smt_friendliness_mean: float, smt_friendliness_std: float) -> None:
        for task in self.tasksThisLevel:
            smt_friendliness = distributions.sample_normal_dist(smt_friendliness_mean, smt_friendliness_std)
            #SMT should not decrease costs
            smt_friendliness = max([smt_friendliness, 1.0])
            for half_ways in range(Constants.MAX_HALF_WAYS+1):
                #task.allUtil_C[half_ways] = {}
                for level in range(self.level, Constants.MAX_LEVEL):
                    util = task.cost_per_cache_crit(half_ways, level)*smt_friendliness/task.period
                    task.set_smt_util_C(half_ways, level, util)
                    #task.allUtil_C[(half_ways,level)] = \
                    #    task.cost_per_cache_crit(half_ways, level)*smt_friendliness/task.period
        return

    def _generate_smt_costs_C_case_study(self, smt_friendliness_mean: float, smt_friendliness_std: float, dataset: str) -> None:
        for task in self.tasksThisLevel:
            smt_friendliness = Constants.SMT_EFFECTIVENESS_C_CASE_STUDY[dataset][task.name]
            #SMT should not decrease costs
            smt_friendliness = max([smt_friendliness, 1.0])
            for half_ways in range(Constants.MAX_HALF_WAYS+1):
                #task.allUtil_C[half_ways] = {}
                for level in range(self.level, Constants.MAX_LEVEL):
                    util = task.cost_per_cache_crit(half_ways, level)*smt_friendliness/task.period
                    task.set_smt_util_C(half_ways, level, util)
                    #task.allUtil_C[(half_ways,level)] = \
                    #    task.cost_per_cache_crit(half_ways, level)*smt_friendliness/task.period
        return

    def _generate_smt_costs(self, smt_dist: Dict[int, Tuple[float,float,float]]) -> None:
        if self.level is Constants.LEVEL_A:
            smt_mean, smt_std, smt_unfriendly = smt_dist[Constants.LEVEL_A]
            self._generate_smt_costs_AB(smt_mean, smt_std, smt_unfriendly)
        elif self.level is Constants.LEVEL_B:
            smt_mean, smt_std, smt_unfriendly = smt_dist[Constants.LEVEL_B]
            self._generate_smt_costs_AB(smt_mean, smt_std, smt_unfriendly)
        else: # only remaining level is C
            smt_mean, smt_std, _unused_smt = smt_dist[Constants.LEVEL_C]
            self._generate_smt_costs_C(smt_mean, smt_std)
        return

    def _generate_smt_costs_case_study(self, smt_dist: Dict[int, Tuple[float,float,float]], dataset: str) -> None:
        if self.level is Constants.LEVEL_A:
            smt_mean, smt_std, smt_unfriendly = smt_dist[Constants.LEVEL_A]
            self._generate_smt_costs_AB_case_study(smt_mean, smt_std, smt_unfriendly, dataset)
        elif self.level is Constants.LEVEL_B:
            smt_mean, smt_std, smt_unfriendly = smt_dist[Constants.LEVEL_B]
            self._generate_smt_costs_AB_case_study(smt_mean, smt_std, smt_unfriendly, dataset)
        else: # only remaining level is C
            smt_mean, smt_std, _unused_smt = smt_dist[Constants.LEVEL_C]
            self._generate_smt_costs_C_case_study(smt_mean, smt_std, dataset)
        return

    def createTasks(self, scenario: Dict[str,str], targetUtil: float, startingID: int, totUtil: float) -> int:

        # Change wss to be from 0 to 32 half-ways
        # expected value of wss to be on average 2 MB (each way is 1 MB)
        # Normal centered at 2 MB with standard deviation of 2 MB
        # truncate low end at 0
        # save results as MB
        # cache allocation possibilities in half-ways from 0-32
        
        #print('createTasks')
        assert(targetUtil >= 0)
        assert(startingID > 0)

        thisLevelUtil=0
        taskID=startingID

        while thisLevelUtil < targetUtil:
            #beware of infinite loops
            assert(taskID - startingID < _MAX_TASKS)
            newTask = self._createTask(taskID, scenario, startingID, totUtil)
            taskID += 1
            newTask_A_util = _task_A_util(newTask)
            if thisLevelUtil + newTask_A_util >= targetUtil:
                _fitTask(newTask, targetUtil - thisLevelUtil)
                self.tasksThisLevel.append(newTask)
                break
            else:
                thisLevelUtil += newTask_A_util
                self.tasksThisLevel.append(newTask)

        # done creating tasks

        #set up SMT costs
        smt_dist = Constants.SMT_EFFECTIVENESS_DIST[scenario['smtEffectDist']]
        self._generate_smt_costs(smt_dist)

        return taskID - startingID

    def loadSystem(self, filename, startingID, targetUtil, dataset):
        taskID = startingID
        util = 0
        case_study = True
        header = True
        with open(filename, "r") as f:
            for line in f:
                if header:
                    header = False
                    continue

                arr = line.split(",")
                #print(arr)
                level = int(arr[3])
                if level == self.level:
                    name = arr[2]
                    period = relDeadline = float(arr[5])
                    baseCost = float(arr[4])/1000
                    baseAcet = Constants.acet_map[dataset][name] #float(arr[4])

                    # compute wss
                    wss_mean, wss_std = Constants.WSS_DIST['Default_WSS']
                    wss = distributions.sample_normal_dist(wss_mean, wss_std)
                    # shouldn't have negative wss, minimum of 32KB is informed by data
                    #wss = max([0.001 * 32, wss])
                    wss = 2
                    '''if dataset == 'TACLe':
                        wss = 0.5
                    if dataset == 'SD-VBS':
                        wss = 1'''
                    #num_times = int(arr[5])
                    # randomly choose task's sensitivity to cache
                    #for i in range(0,num_times):
                        #cache_sense_dist = Constants.CACHE_SENSITIVITY['Default_Sensitivity']
                        #cache_sense = distributions.sample_choice(cache_sense_dist)
                        #print(dataset,name)
                    cache_sense = Constants.cacheSensitivityMapping[dataset][name]
                    newTask = Task(taskID, self.level, baseCost, period, relDeadline, wss, cache_sense, startingID, targetUtil, baseAcet, case_study)
                    newTask.name = name
                    self.tasksThisLevel.append(newTask)
                    taskID += 1
                        #print(newTask.ID, newTask.name, newTask.level, baseCost, period, wss, cache_sense)
                        #util += baseCost/period
        #print(util)
        smt_dist = Constants.SMT_EFFECTIVENESS_DIST['DIS_SMTv2']
        self._generate_smt_costs_case_study(smt_dist, dataset)
        return taskID


    def setAllSolo(self):
        if self.level is Constants.LEVEL_A or self.level is Constants.LEVEL_B:
            for task in self.tasksThisLevel:
                self.thePairs.append((
                    task.ID,
                    task.ID,
                    get_pair_util(task,task,self.level,
                                  self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,
                                  self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2
                    )
                ))
        else:
            for task in self.tasksThisLevel:
                task.currentSoloUtil = get_pair_util(task, task, self.level, self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,
                                                         self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2)
                self.soloTasks.append(task)
                self.totalSoloUtil += task.currentSoloUtil
        return

    #applies to crit levels A and B
    def setPairsList(self) -> int:
        if len(self.tasksThisLevel) == 0:
            #no tasks, no pairs.
            return GRB.OPTIMAL
        pairsILP = MakePairsILP(self)
        self.thePairs, self.timeToPair, gStatus = pairsILP.makePairs()
        #print('Time to pair = %d' % int(self.timeToPair))
        #print("Printing thePairs")
        #print(self.thePairs)
        #for task1ID, task2ID, pairUtil in self.thePairs:
        #    assert(task1ID == task2ID)
        return gStatus

    #applies to crit levels A and B
    def assignToCores(self, alg, coreList, dedicatedIRQ: bool=False) -> bool:
        """
        Assign tasks to cores, applicable to level-A and -B tasks
        :param dedicatedIRQ: is core 0 a dedicatedIRQ core which we do not schedule work on
        :param alg: partitioning algorithm, unused
        :param coreList: list of cores
        :return:
        """
        # to-do: implement a second method for period-aware worst-fit
        # should this change each core's list of tasks?
        # using 0-indexed cores
        #startingTaskID=self.tasksThisLevel[0].ID
        if len(self.thePairs) == 0:
            #We want to test with empty crit levels now
            return True
            #raise NotImplementedError

        if Constants.VERBOSE:
            print('Assignment algorithm %d' % alg)

        thePairs = self.thePairs

        sortedPairs = sorted(thePairs, key=lambda x: x[2], reverse=True)

        # pair = (task1, task2, pairUtil)
        for pair in sortedPairs:
            bestCoreSoFar = -1
            utilOnBest = Constants.ASSUMED_MAX_CAPACITY
            task1=self.getTask(pair[0])
            task2=self.getTask(pair[1])
            pairUtil = pair[2] #self.tasksThisLevel[task1-startingTaskID]._allUtil[(task2, self.level, self.assumedCache)]

            #for c in coreList:
            #skip core 0 if it's the dedicated interrupt core
            for c in range(1 if dedicatedIRQ else 0, len(coreList)):
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
                for critLevel in range(self.level+1,Constants.MAX_LEVEL):
                    #coreList[bestCoreSoFar].utilOnCore[critLevel] += self.tasksThisLevel[task1-startingTaskID]._allUtil[(task2, critLevel, self.assumedCache)]
                    #assume each thread gets half the whole L3 here
                    coreList[bestCoreSoFar].utilOnCore[critLevel] += get_pair_util(
                        task1, task2, critLevel,
                        self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,
                        self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2
                    )
        # returns only if all pairs could be placed on a core
        # return pairsByCore
        return True


    #applies to crit level C
    def decideThreaded(self):
        """
        Decide which tasks should be threaded/ unthreaded.
        Recall from ECRTS '19 that the oblivious approach is not bad;
        Exact approach to partitioning doesn't make that much difference.

        Because friendliness at C does not depend on the sibling task, it is sufficient to only check one other task

        In any cache, we need an assumed cache level to start.
        """
        firstTask=True
        for thisTask in self.tasksThisLevel:
            #Note the latter cache value is unused by this function
            thisTask.currentSoloUtil=get_pair_util(thisTask,thisTask,self.level,
                                                   self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,self.assumedCache
            )
            
            if firstTask:
                if len(self.tasksThisLevel) >= 2:
                    otherTask=self.tasksThisLevel[1]
                    firstTask = False
                else:
                    self.soloTasks.append(thisTask)
                    self.totalSoloUtil += thisTask.currentSoloUtil
                    break
            else:
                otherTask=self.tasksThisLevel[0]
            
            #print()
            #print("Printing level C task.")
            #print("taskID=", thisTask.ID)
            #print(thisTask._allUtil)
            
            threadedUtil= get_pair_util(thisTask, otherTask, self.level,
                                        self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,
                                        self.assumedCache//Constants.SIZE_OF_HALF_WAYS//2
            )
            #thisTask._allUtil[(otherTask.ID, self.level, self.assumedCache)]
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
                #assert False

    #applies to level C only
    def divideCores(self, coreList, coresPerComplex, dedicatedIRQ: bool = False) -> bool:
        #determine cores needed for solos
        soloCapacity=0
        c = 1 if dedicatedIRQ else 0
        while soloCapacity < self.totalSoloUtil:
            soloCapacity = soloCapacity + 1-coreList[c].utilOnCore[Constants.LEVEL_C]
            self.soloCores.append(coreList[c])
            c +=1
            if c ==len(coreList):
                #can't do all the solo tasks; return failure
                return False
        #print("Prelim. solo cores:")
        #for  core in self.soloCores:
        #    print(core.coreID, end=",")
        #print()

        #determine cores needed for threaded
        threadedCapacity=0
        c = len(coreList)-1
        remainingCores = len(coreList)-len(self.soloCores) - (1 if dedicatedIRQ else 0)
        while threadedCapacity < self.totalThreadedUtil:
            threadedCapacity = threadedCapacity + 2*(1-coreList[c].utilOnCore[Constants.LEVEL_C])
            self.threadedCores.append(coreList[c])
            c -=1
            remainingCores -=1
            if remainingCores < 0:
                return False
        #print("Prelim. threadedCores cores:")
        #for core in self.threadedCores:
        #    print(core.coreID, end=",")
        #print()

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
        #numSoloClusters=math.ceil(len(self.soloCores)/coresPerComplex)

        c = 1 if dedicatedIRQ else 0
        clusterCores = []
        while c - (1 if dedicatedIRQ else 0) < len(self.soloCores):
            clusterCores.append(coreList[c])
            if (c + 1) % coresPerComplex == 0:
                thisCluster = Cluster(clusterCores, False)
                self.soloClusters.append(thisCluster)
                clusterCores = []
            c += 1
        if len(clusterCores) > 0:
            thisCluster = Cluster(clusterCores, False)
            self.sharedSoloCluster = thisCluster
            self.soloClusters.append(thisCluster)

        #numThreadedClusters=math.ceil(len(self.threadedCores)/coresPerComplex)
        #print("numThreadedClusters: ", numThreadedClusters)
        #sizeLastSoloCluster=len(self.soloClusters[numSoloClusters-1].clusterCores)
        # deal with odd-sized threaded cluster, if it exists
        j=len(self.soloCores) + (1 if dedicatedIRQ else 0)
        clusterCores=[]
        while j <len(coreList):
            clusterCores.append(coreList[j])
            if (j+1) % coresPerComplex==0:
                thisCluster=Cluster(clusterCores, True)
                if self.sharedSoloCluster is not None and self.sharedThreadedCluster is None:
                    self.sharedThreadedCluster = thisCluster
                self.threadedClusters.append(thisCluster)
                clusterCores=[]
            j+=1
            #print("j=", j)
        #coresPerComplex should evenly divide the number of cores
        assert(len(clusterCores) == 0)

        return True

            

    #applies to level C only
    def assignTasksToClusters(self) -> bool:
        """
        For each set of tasks:
        --sort by non-increasing util.
        --assign to clusters via worst-fit (most space remaining) + testAndAddTask
        --sort clusters by increasing space remaining
        --testAndAddTask until we find something that fits
        --if nothing fits, fail
        """

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
            if cluster is not self.sharedSoloCluster:
                #single cluster in this complex
                complexList[complexNo].clusterList.append(cluster)
                complexList[complexNo].coreList = cluster.coresThisCluster
                complexNo += 1
        for cluster in self.threadedClusters:
            if cluster is not self.sharedThreadedCluster:
                #single cluster in this complex
                complexList[complexNo].clusterList.append(cluster)
                complexList[complexNo].coreList = cluster.coresThisCluster
                complexNo += 1

        if self.sharedSoloCluster is not None or self.sharedThreadedCluster is not None:
            #should only get here if a single cluster is shared
            assert(self.sharedSoloCluster is not None and self.sharedThreadedCluster is not None)
            complexList[complexNo].clusterList.append(self.sharedSoloCluster)
            complexList[complexNo].clusterList.append(self.sharedThreadedCluster)
            complexList[complexNo].coreList = []
            complexList[complexNo].coreList.extend(self.sharedSoloCluster.coresThisCluster)
            complexList[complexNo].coreList.extend(self.sharedThreadedCluster.coresThisCluster)

    def assignClusterID(self):
        if self.level == Constants.LEVEL_C:
            clus_id = 0
            for cluster in self.soloClusters:
                cluster.clusterID = clus_id
                clus_id += 1
            for cluster in self.threadedClusters:
                cluster.clusterID = clus_id
                clus_id += 1

    def get_pair_cost_AB(self, pair, costLevel,cacheSize):
        thisPairPeriod = self.getTask(pair[0]).period
        if pair[0] != pair[1]:
            thisPairUtil = get_pair_util(
                self.getTask(pair[0]),
                self.getTask(pair[1]),
                costLevel,
                cacheSize[0],
                cacheSize[1]
            )
        else:
            thisPairUtil = get_pair_util(
                self.getTask(pair[0]),
                self.getTask(pair[1]),
                costLevel,
                cacheSize[0],
                cacheSize[1]
            )

            # tasksCritLevel[pair[0] - startingTaskID]._allUtil[(pair[1], costLevel, min(cacheSize) * 2)]
        thisPairCost = thisPairUtil * thisPairPeriod
        return thisPairCost

    def get_task_cost_C(self,task,clusterTasks,threaded,cacheSize):
        thisPairPeriod = task.period
        if threaded:
            thisPairUtil = 0
            for otherTask in clusterTasks:
                if task != otherTask:
                    thisPairUtil = max([
                        thisPairUtil,
                        get_pair_util(task, otherTask, Constants.LEVEL_C, cacheSize, cacheSize)
                    ])
                    # task._allUtil[(otherTask.ID, Constants.LEVEL_C, cacheSize)])
            thisPairCost = thisPairUtil * thisPairPeriod
        else:
            thisPairCost = get_pair_util(task, task, Constants.LEVEL_C, cacheSize, cacheSize) * task.period
        return thisPairCost

    def printCoreAssignment(self,coreList):
        #critLevel = self.level
        startingTaskID = self.tasksThisLevel[0].ID
        for c in range(len(coreList)):
            print("core: ",c)
            for pair in coreList[c].pairsOnCore[self.level]:
                print("<",self.tasksThisLevel[pair[0]-startingTaskID].ID,",",self.tasksThisLevel[pair[1]-startingTaskID].ID,">",end=" ")
            print(coreList[c].utilOnCore[self.level])

'''
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
'''
#if __name__== "__main__":
#     main()

def compareCritLevel(cl1: CritLevelSystem, cl2: CritLevelSystem):
    #self.level: int = level
    assert(cl1.level is cl2.level)

    assert(len(cl1.thePairs) is len(cl2.thePairs))
    for pair in cl1.thePairs:
        assert(pair in cl2.thePairs)
    #self.thePairs = []
    #self.timeToPair = 0
    #self.tasksThisLevel = []
    assert(len(cl1.tasksThisLevel) is len(cl2.tasksThisLevel))
    for task in cl1.tasksThisLevel:
        assert(task in cl2.tasksThisLevel)

    assert(cl1.assumedCache is cl2.assumedCache)
    #self.assumedCache = assumedCache
    if cl1.level == Constants.LEVEL_C:
        #self.soloTasks = []
        assert(len(cl1.soloTasks) is len(cl2.soloTasks))
        for task in cl1.soloTasks:
            assert(task in cl2.soloTasks)
        #self.threadedTasks = []
        assert(len(cl1.threadedTasks) is len(cl2.threadedTasks))
        for task in cl1.threadedTasks:
            assert(task in cl2.threadedTasks)
        #self.totalSoloUtil = 0
        assert(-1e9 < cl1.totalSoloUtil - cl2.totalSoloUtil < 1e9)
        #self.totalThreadedUtil = 0
        assert(-1e9 < cl1.totalThreadedUtil - cl2.totalThreadedUtil < 1e9)
        #self.threadedCores = []
        assert(len(cl1.threadedCores) is len(cl2.threadedCores))
        for idx in range(len(cl1.threadedCores)):
            compCore(cl1.threadedCores[idx], cl2.threadedCores[idx])
        assert(len(cl1.soloCores) is len(cl2.soloCores))
        for idx in range(len(cl1.soloCores)):
            compCore(cl1.soloCores[idx], cl2.soloCores[idx])
        #self.soloCores = []
        assert(len(cl1.soloClusters) is len(cl2.soloClusters))
        for idx in range(len(cl1.soloClusters)):
            compCluster(cl1.soloClusters[idx], cl2.soloClusters[idx])
        #self.soloClusters = []
        assert(len(cl1.threadedClusters) is len(cl2.threadedClusters))
        for idx in range(len(cl1.threadedClusters)):
            compCluster(cl1.threadedClusters[idx], cl2.threadedClusters[idx])
        #self.threadedClusters = []
        if cl1.sharedSoloCluster is None:
            assert(cl2.sharedSoloCluster is None)
        else:
            compCluster(cl1.sharedSoloCluster, cl2.sharedSoloCluster)
        #self.sharedSoloCluster = None
        if cl1.sharedThreadedCluster is None:
            assert(cl2.sharedThreadedCluster is None)
        else:
            compCluster(cl1.sharedThreadedCluster, cl2.sharedThreadedCluster)
