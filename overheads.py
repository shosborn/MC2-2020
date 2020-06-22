from csv import DictReader
from collections import defaultdict
from constants import Constants
import pandas as pd
import math
from task import Task


class Overheads:

    def __init__(self):
        self.overheadData = None
        self.overheadValue = defaultdict()

        for key in Constants.OVERHEAD_TYPES:
            self.overheadValue[key] = defaultdict()
            for level in range(Constants.LEVEL_A,Constants.LEVEL_C+1):
                self.overheadValue[key][level] = defaultdict()

        self.denom = {}
        self.cPre = {}

        self.cpmd = {}
        self.cpmdInflationLevelAB = {}

    def loadOverheadData(self,dirName):
        '''
        Load overhead data to self.overheadData after making the data monotonic
        :param dirName: directory where overhead data are stored
        :return:
        '''
        critMap = {'A':0, 'B': 1, 'C':2}
        overheadData = defaultdict()
        for critLevelKey  in critMap:
            critLevelValue = critMap[critLevelKey]
            overheadData[critLevelValue] = defaultdict()
            fileName = dirName + "//ovh_" + critLevelKey + "_mc2" + ".csv"
            overheadData[critLevelValue] = pd.read_csv(fileName, index_col=0)
            for column in range(overheadData[critLevelValue].shape[1]):
                maxValue = -1
                for row in range(overheadData[critLevelValue].shape[0]):
                    maxValue = max(maxValue,overheadData[critLevelValue].iloc[row,column])
                    overheadData[critLevelValue].iloc[row, column] = maxValue #make monotonic
            #if critLevelValue == Constants.LEVEL_A:
            #    print(overheadData[critLevelValue])
        self.overheadData = overheadData

    def montonicInterpolation(self,taskCount,costLevel,overhead):
        '''
        interpolate overhead value of an overhead type for arbitrary task count from overhead data by piecewise linear interpolation
        if task count is greater than the max task count in overhead data, then the value for max task count
        is returned, i.e., max overhead value in the data
        :param taskCount: number of tasks
        :param costLevel: execution criticality level for overhead data
        :param overhead: overhead type, column header of csv file
        :return: interpolated value
        '''

        numTasks = list(self.overheadData[costLevel].index)
        overheadData = self.overheadData[costLevel][overhead]
        if taskCount < numTasks[0]:
            return overheadData.iloc[0]
        if taskCount > numTasks[-1]:
            return overheadData.iloc[-1]
        start = 0
        end = len(numTasks)-1
        mid = int(len(numTasks)/2)
        while numTasks[mid] != taskCount:
            if taskCount < numTasks[mid]:
                end = mid-1
            else:
                start = mid+1
            if start > end:
                break
            mid = int((start+end)/2)
        if numTasks[mid] == taskCount:
            return overheadData.iloc[mid]
        if numTasks[mid] > taskCount:
            return overheadData.iloc[mid-1] + (overheadData.iloc[mid]-overheadData.iloc[mid-1])/(numTasks[mid]-numTasks[mid-1])*\
                   (taskCount-overheadData.iloc[mid-1])
        if numTasks[mid] < taskCount:
            return overheadData.iloc[mid] + (overheadData.iloc[mid+1] - overheadData.iloc[mid]) / (
                        numTasks[mid+1] - numTasks[mid]) * \
                   (taskCount - overheadData.iloc[mid])


    def linearInterpolation(self,taskCount,costLevel,overhead):
        '''
        interpolate overhead value of an overhead type for arbitrary task count from overhead data by piecewise linear interpolation
        if task count is greater than the max task count in overhead data,
        then the value is linearly interplated using median task count and max task count
        :param taskCount: number of tasks
        :param costLevel: execution criticality level for overhead data
        :param overhead: overhead type, column header of csv file
        :return: interpolated value
        '''

        numTasks = list(self.overheadData[costLevel].index)
        overheadData = self.overheadData[costLevel][overhead]
        if taskCount < numTasks[0]:
            return overheadData.iloc[0]
        if taskCount > numTasks[-1]:
            mid = int(len(numTasks)/2)
            return overheadData.iloc[mid] + (overheadData.iloc[-1]-overheadData.iloc[mid])/(numTasks[-1]-numTasks[mid])*\
                   (taskCount-overheadData.iloc[mid])
        start = 0
        end = len(numTasks)-1
        mid = int(len(numTasks)/2)
        while numTasks[mid] != taskCount:
            if taskCount < numTasks[mid]:
                end = mid-1
            else:
                start = mid+1
            if start > end:
                break
            mid = int((start+end)/2)
        if numTasks[mid] == taskCount:
            return overheadData.iloc[mid]
        if numTasks[mid] > taskCount:
            return overheadData.iloc[mid-1] + (overheadData.iloc[mid]-overheadData.iloc[mid-1])/(numTasks[mid]-numTasks[mid-1])*\
                   (taskCount-overheadData.iloc[mid-1])
        if numTasks[mid] < taskCount:
            return overheadData.iloc[mid] + (overheadData.iloc[mid+1] - overheadData.iloc[mid]) / (
                        numTasks[mid+1] - numTasks[mid]) * \
                   (taskCount - overheadData.iloc[mid])

    def getOverheadValue(self,taskCount,costLevel,overhead):
        '''
        get overhead value by taskcount.
        :param taskCount: number of tasks
        :param costLevel: execution criticality level for overhead data
        :param overhead: overhead type for which value is derived
        :return:
        '''
        if overhead == 'CPMD': #cache related preemption and migration delay
            raise NotImplementedError
        # for any taskcount > max # of tasks in overhead data, maxmimum observed overhead value is used (maybe data need to be observed)
        return self.montonicInterpolation(taskCount,costLevel,overhead)


    def getCPMDLevelA(self,pairs,tasks,core,cacheSize,scheme):
        '''
        calculate cache related preemption delay of level-A tasks of a core
        task-centric accounting of level-A tasks according to N.Kim et al real-time systems journal paper.
        Applies for cache related delays caused by preemption of a level-A task by another level-A task
        (Delay for preemption of a level-B task by a level-A task is accounted by CPMDInflationLevelAB)
        This is used when MC^2 use budgeted implementation for level-A tasks
        If PET for all job-slices of level-A can be predetermined, then 0 CPMD cost for level-A can be used.
        :param pairs: pairs of criticality level-'taskLevel' assigned to a core/ core-complex
        :param tasks: all tasks at criticality level-'taskLevel'
        :param core: considered core
        :param cacheSize: cachesize allocated to the pairs at 'taskLevel' of a core (for level-B) or core-complex (for level-C)
        :param scheme: cache allocation scheme
        :return: A dictionary of (pair, execution level)->cpmd cost
        '''
        cpmd = {}
        if len(pairs) == 0:
            return cpmd
        startingTaskID = tasks[0].ID
        minPeriod = core.minLevelAPeriod

        for pair in pairs:
            numSlices = tasks[pair[0]-startingTaskID].period / minPeriod  #n.kim et al journal paper page 27

            if scheme == Constants.THREAD_LEVEL_ISOLATION:
                # for paired task max cache size among two threads dominates
                # solo task can use min cache size * 2 (since can see full way)
                cachePair = max(cacheSize) if pair[0]!=pair[1] else min(cacheSize) * 2
            else:
                #core-level isolation, same cachesize to be cosidered for both solo and paired
                cachePair = cacheSize[0]+cacheSize[1]

            for costLevel in range(Constants.LEVEL_A, Constants.LEVEL_C+1):
                inflation = (numSlices - 1) * min(tasks[pair[0]-startingTaskID].getWss(),cachePair) * Constants.CPMD_PER_UNIT[costLevel]
                cpmd[(pair,costLevel)] = inflation

        return cpmd

    def getCPMDLevelB(self,pairs,tasks,cacheSize,scheme):
        '''
        calculate preemption-centric cache related preemption and migration delay for a core.
        applies for preemption of level-B tasks by level-B tasks
        wss is assumed to be stored in task.py
        :param pairs: pairs of criticality level-'taskLevel' assigned to a core/ core-complex
        :param tasks: all tasks at level-'taskLevel'
        :param cacheSize: cachesize allocated to the pairs at 'taskLevel' of a core (for level-B) or core-complex (for level-C)
        :param scheme: cache allocation scheme
        :return: A dictionary of execution level -> cost
        '''

        if len(pairs) <= 1:
            #no cpmd in same level if 0 or 1 tasks in core
            return {Constants.LEVEL_B:0,Constants.LEVEL_C:0}

        startingTaskID = tasks[0].ID

        #maximum wss among the two tasks of a pair dominate, for solo also works pair[0]==pair[1]
        effectivePairWSS = [max(tasks[pair[0]-startingTaskID].getWss(),tasks[pair[1]-startingTaskID].getWss()) for pair in pairs]

        maxWSS = max(effectivePairWSS)

        if scheme==Constants.THREAD_LEVEL_ISOLATION:
            #maxmimum among what can be seen by threaded or solo tasks
            effectiveCacheThread = max(max(cacheSize), min(cacheSize)*2)
        else:
            #for core-level, whole cache of this core
            effectiveCacheThread = cacheSize[0] + cacheSize[1]

        cpmd = {}
        for costLevel in (Constants.LEVEL_B,Constants.LEVEL_C):
            inflation = min(maxWSS, effectiveCacheThread) * Constants.CPMD_PER_UNIT[costLevel]
            cpmd[costLevel] = inflation

        return cpmd

    def getCPMDLevelC(self,clusterTasks,cacheSize):
        '''
        calculate preemption-centric cache related preemption and migration delay for a cluster.
        applies for preemption of level-C tasks by level-C tasks
        :param clusterTasks: tasks of the cluster for which
        :param costLevel: criticality level of execution
        :param cacheSize: cachesize allocated (in half ways)
        :return: A pair of (taskpair,cpmdCost)
        '''

        if len(clusterTasks) <= 1:
            #no cpmd in same level if 0 or 1 tasks per core/core-complex
            return {Constants.LEVEL_C:0}

        maxWSS = max(task.getWss() for task in clusterTasks)

        #works for core-level cache isolation too
        cpmd = {}
        inflation = min(maxWSS, cacheSize) * Constants.CPMD_PER_UNIT[Constants.LEVEL_C]
        cpmd[Constants.LEVEL_C] = inflation

        return cpmd

    def CPMDInflationLevelAB(self,pairs,core,allCriticalityLevels,cacheSize,scheme,dedicatedIRQ=False,dedicatedIRQCore=False):
        '''
        extra utilization term for a core at level-B,-C analysis due to level-A tasks preempting level-B tasks and affect their cache affinity
        :param pairs: level-B pairs of a core
        :param tasks: all tasks at level-B
        :param costLevel: level of execution to be considered
        :param core: for which core
        :param dedicatedIRQ: is dedicated interrupt or not
        :param dedicatedIRQCore: if dedicated interrupts then the core handling interrupts
        :return: utilization term need to be added
        '''
        #no level-B task in this core
        if len(pairs) == 0:
            return {Constants.LEVEL_B:0, Constants.LEVEL_C:0}

        #otherwise
        tasks = allCriticalityLevels[Constants.LEVEL_B].tasksThisLevel #level-B tasks
        startingTaskID = tasks[0].ID #level-B tasks starting ID
        minPeriod = core.minLevelAPeriod

        effectivePairWSS = [max(tasks[pair[0] - startingTaskID].getWss(), tasks[pair[1] - startingTaskID].getWss()) for pair in
                            pairs]
        maxWSS = max(effectivePairWSS)

        if scheme == Constants.THREAD_LEVEL_ISOLATION:
            # maxmimum among what can be seen by threaded or solo tasks
            effectiveCacheThread = max(max(cacheSize), min(cacheSize) * 2)
        else:
            # for core-level, whole cache of this core
            effectiveCacheThread = cacheSize[0] + cacheSize[1]

        cpmdUtil = {}
        for costLevel in (Constants.LEVEL_B,Constants.LEVEL_C):
            cpmd = min(maxWSS,effectiveCacheThread) * Constants.CPMD_PER_UNIT[costLevel]

            #for this extra term account for tick and release (need this? miccaiah's paper doesn't explicitely says)
            if dedicatedIRQ and core != dedicatedIRQCore:
                #if dedicated interrupt but this core is not handling, then use don't need irq
                denom, cpre = self.denom[False][costLevel], self.cPre[False][costLevel]
            else:
                denom, cpre = self.denom[False][costLevel], self.cPre[False][costLevel]

            cpmdUtil[costLevel] = (cpmd / denom)/minPeriod #the term I^B_{A,p} of rts journal 15 paper, page 28

        return cpmdUtil

    def irqCosts(self, allCritLevels, considerIRQ=False):
        '''
        compute values to account irq overheads accross 3 levels of execution
        :param allCritLevels: list of all criticality level objects (since all tasks are needed here)
        :param considerIRQ: whether release interrupts to consider or not
        :return:
        '''
        denomAll , cPreAll = {}, {}
        for costLevel in range(Constants.LEVEL_A,Constants.LEVEL_C+1):
            tick = self.overheadValue['tick'][costLevel] #Delta_tck
            releaseLatency = self.overheadValue['releaseLatency'][costLevel] #Delta_ev
            release = self.overheadValue['release'][costLevel] #Delta_rel

            eTick = (tick + Constants.CPI_PER_UNIT[costLevel]) #page 251
            eIrq = (release + Constants.CPI_PER_UNIT[costLevel]) #page 251
            uTick = eTick / Constants.QUANTUM_LENGTH #page 251

            uRelease = 0 #third term of denominator of Expression 3.17
            cPre = eTick + releaseLatency * uTick  # first two terms of numerator of 3.18

            if considerIRQ:
                for critLevel in allCritLevels:
                    for task in critLevel.tasksThisLevel:
                        uIrq = (eIrq / task.period)
                        uRelease += uIrq # u^irq = (eIrq /task.period), page 251 (there may be a typo in page 251 about this eqn)
                        cPre += releaseLatency * uIrq + eIrq  # third term of numerator of 3.18

            denominator = (1- uTick - uRelease) #denominator of 3.17
            cPre /= denominator #3.18 complete

            denomAll[costLevel] = denominator
            cPreAll[costLevel] = cPre

        #self.denom = denomAll
        #self.cPre = cPreAll
        return denomAll, cPreAll


    def populateIRQCosts(self,allCriticalityLevels):
        '''
        populate demon and cpre values for accounting interrupts (both considering release interrupts and not)
        :param allCriticalityLevels: all criticality levels
        :return:
        '''
        # considering release interrupt cost (usage: if not dedicated interrupt or for the core handling interrupt if dedicated interrupt used)
        self.denom[True], self.cPre[True] = self.irqCosts(allCriticalityLevels, True)
        # not considering release interrupt (usage: for cores not handling interrupts in dedicated interrupt handling)
        self.denom[False], self.cPre[False] = self.irqCosts(allCriticalityLevels, False)

    def populateOverheadValue(self,taskCount,allCriticalityLevels):
        '''
        populate all overhead values for no of tasks=taskcount
        :param taskCount: no of tasks
        :param allCriticalityLevels: all criticality levels
        :return:
        '''
        for oheadName in Constants.OVERHEAD_TYPES:
            oHeadCode = Constants.OVERHEAD_TYPES[oheadName]
            for costLevel in range(Constants.LEVEL_A, Constants.LEVEL_C+1):
                self.overheadValue[oheadName][costLevel] = self.getOverheadValue(taskCount,costLevel,oHeadCode)
        self.populateIRQCosts(allCriticalityLevels)

    def accountOverheadCore(self, taskLevel, allCritLevels, core, cacheSize, scheme, dedicatedIRQ=False, dedicatedIRQCore=None):
        '''
        Account for overhead of level-A or -B tasks of a core
        :param taskLevel: taskss' criticality level
        :param allCritLevels: list of all criticality levels
        :param core: core for which overhead is accounted
        :param cacheSize size of allocated cache
        :param scheme scheme of level-A,-B cache allocation
        :param dedicatedIRQ whether dedicated interrupt handling or not
        :param dedicatedIRQCore which core is handling interrupt in case of dedicated interrupt handling
        :return: A dictionary of pair -> util after accounting overheads
        '''
        #store inflated pairs. Not altering original tasks parameters. They may be needed to compare with other schedulers.
        inflatedUtils = defaultdict()

        tasksCritLevel = allCritLevels[taskLevel].tasksThisLevel
        startingTaskID = tasksCritLevel[0].ID

        #cache delay for all pairs at this level of this core
        if taskLevel == Constants.LEVEL_A:
            # for budgeted implementation of cyclic executing. ref. n.kim journal paper 2017
            cpmd = self.getCPMDLevelA(pairs=core.pairsOnCore[taskLevel], tasks=tasksCritLevel,scheme=scheme,
                                       cacheSize=cacheSize, core=core)  # dictionary of (pair,costLevel)->cost
        else:
            cpmd = self.getCPMDLevelB(pairs=core.pairsOnCore[taskLevel], tasks=tasksCritLevel,
                                        scheme=scheme,cacheSize=cacheSize)

        #consider all criticality levels at or below for the tasks at critLevel
        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
            # ipi overhead value at execution of costLevel
            ipi = self.overheadValue['ipiLatency'][costLevel]

            # get scheduling and context switch overhead assuming execution at criticality level 'costLevel'
            schedOverhead = self.overheadValue['scheduling'][costLevel]
            contextSwitch = self.overheadValue['contextSwitch'][costLevel]

            releaseLatency = self.overheadValue['releaseLatency'][costLevel]  # Delta_ev

            smtOverhead = Constants.SMT_OVERHEAD[costLevel]

            #if Constants.DEBUG:
            #    print("cost level: ",costLevel)
            #    print("ipi: ",ipi, " sched: ", schedOverhead, " ctx: ",contextSwitch, " relLatency: ", releaseLatency, " smt: ", smtOverhead)

            #identify if this core is the dedicate interrupt core or this cluster contains that core
            isDedicatedInterruptCore = False
            if dedicatedIRQ:
                isDedicatedInterruptCore = (core == dedicatedIRQCore)

            for pair in core.pairsOnCore[taskLevel]:
                #cost of this task/pair assuming execution at critcality level-'level'
                thisPairPeriod = tasksCritLevel[pair[0] - startingTaskID].period
                #paired task
                if pair[0] != pair[1]:
                    #cost is currently modeled based on total cache for the pair, not how they are divided
                    #this is ok for core-level-isolation, but what about thread-level-isolation? 2+2 vs 3+1?
                    thisPairUtil = tasksCritLevel[pair[0]-startingTaskID].allUtil[(pair[1], costLevel,  cacheSize[0]+cacheSize[1])]
                #solo task
                else:
                    thisPairUtil = tasksCritLevel[pair[0] - startingTaskID].allUtil[(pair[1], costLevel,
                                         cacheSize[0] + cacheSize[1])] if scheme==Constants.CORE_LEVEL_ISOLATION else tasksCritLevel[
                                                    pair[0] - startingTaskID].allUtil[(pair[1], costLevel, min(cacheSize)*2)]

                thisPairCost = thisPairUtil * thisPairPeriod
                origCost = thisPairCost

                if taskLevel == Constants.LEVEL_A:
                    # add cpmd overhead
                    thisPairCost += cpmd[(pair,costLevel)]
                    # ctx switch overhead for each slice and single sched overhead, num_slices * ctx + sched
                    thisPairCost += (thisPairPeriod / core.minLevelAPeriod) * contextSwitch + schedOverhead
                    #smt overhead similar to ctx overhead
                    thisPairCost += (thisPairPeriod / core.minLevelAPeriod) * smtOverhead
                else:
                    thisPairCost += cpmd[costLevel]
                    thisPairCost += 2 * (schedOverhead + contextSwitch)
                    thisPairCost += 2 * smtOverhead

                #inflate for isr
                if dedicatedIRQ and not isDedicatedInterruptCore:
                    thisPairCost /= self.denom[False][costLevel]
                    thisPairCost += 2 * self.cPre[False][costLevel] + ipi

                    # update cost acc. to page 263
                    release = self.overheadValue['release'][costLevel]
                    thisPairCost += release
                else:
                    thisPairCost /= self.denom[True][costLevel]
                    thisPairCost += 2 * self.cPre[True][costLevel] + ipi

                    # update period by (3.3) page 262
                    thisPairPeriod -= releaseLatency

                #inflatedPairs[critLevel][pair] = (thisPairPeriod,thisRelDeadline,thisPairCost)
                inflatedUtils[(pair,costLevel)] = thisPairCost/thisPairPeriod
                if Constants.DEBUG:
                    print("pair: ",pair, "exec level: ",costLevel, " orig cost: ", origCost, "inflated cost: ", thisPairCost)
        return inflatedUtils

    def accountOverheadCluster(self, taskLevel, allCritLevels, cluster, cacheSize, additionalCluster=None, dedicatedIRQ=False, dedicatedIRQCore=None):
        '''
        Account for overhead for level-C tasks of a cluster
        :param taskLevel: tasks' level (level-C)
        :param allCritLevels: list of all criticality levels
        :param cluster: cluster for which overhead is accounted
        :param cacheSize: size of allocated cache
        :param additionalCluster for a single core complex, there can be two clusters (one solo, one threaded). need the additionalCluster for level-C cache delay measuring
        :param dedicatedIRQ whether dedicated interrupt handling or not
        :param dedicatedIRQCore which core is handling interrupt in case of dedicated interrupt handling
        :return: A dictionary of (taskID,execLevel) -> util after accounting overheads
        '''
        #store inflated pairs. Not altering original tasks parameters. They may be needed to compare with other schedulers.
        inflatedUtils = defaultdict()

        tasksCritLevel = allCritLevels[taskLevel].tasksThisLevel
        startingTaskID = tasksCritLevel[0].ID

        if additionalCluster:
            tasks = []
            tasks.extend(cluster.taskList)
            tasks.extend(additionalCluster.taskList)
            cpmd = self.getCPMDLevelC(clusterTasks=tasks,
                                      cacheSize=cacheSize)
        else:
            cpmd = self.getCPMDLevelC(clusterTasks=cluster.taskList,
                                cacheSize=cacheSize)

        #consider all criticality levels at or below for the tasks at critLevel
        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
            # ipi overhead value at execution of costLevel
            ipi = self.overheadValue['ipiLatency'][costLevel]

            # get scheduling and context switch overhead assuming execution at criticality level 'costLevel'
            schedOverhead = self.overheadValue['scheduling'][costLevel]
            contextSwitch = self.overheadValue['contextSwitch'][costLevel]

            releaseLatency = self.overheadValue['releaseLatency'][costLevel]  # Delta_ev

            #identify if this core is the dedicate interrupt core or this cluster contains that core
            isDedicatedInterruptCore = False
            if dedicatedIRQ:
                for core in cluster.coresThisCluster:
                    isDedicatedInterruptCore = (core == dedicatedIRQCore)
                    if isDedicatedInterruptCore:
                        break

            for task in cluster.taskList:
                #cost of this task/pair assuming execution at critcality level-'level'
                thisPairPeriod = task.period

                if cluster.threaded:
                    thisPairUtil = 0
                    for otherTask in cluster.taskList:
                        if task != otherTask:
                            thisPairUtil = max(thisPairUtil, task.allUtil[(otherTask.ID,Constants.LEVEL_C,cacheSize)])
                    thisPairCost = thisPairUtil * thisPairPeriod
                else:
                    thisPairCost = task.allUtil[(task.ID,Constants.LEVEL_C,cacheSize)] * thisPairPeriod
                origCost = thisPairCost

                thisPairCost += cpmd[costLevel]
                thisPairCost += 2 * (schedOverhead + contextSwitch)

                # no smt overhead accounted for level-C tasks
                # preemptions due to level-C tasks do not need any smt turning off or on
                # since a level-C task can only preempt another level-C tasks
                # and all level-C tasks of a cluster is either solo or threaded

                #inflate for isr
                if dedicatedIRQ and not isDedicatedInterruptCore:
                    thisPairCost /= self.denom[False][costLevel]
                    thisPairCost += 2 * self.cPre[False][costLevel] + ipi

                    # update cost acc. to page 263
                    release = self.overheadValue['release'][costLevel]
                    thisPairCost += release
                else:
                    thisPairCost /= self.denom[True][costLevel]
                    thisPairCost += 2 * self.cPre[True][costLevel] + ipi

                    # update period by (3.3) page 262
                    thisPairPeriod -= releaseLatency

                #inflatedPairs[critLevel][pair] = (thisPairPeriod,thisRelDeadline,thisPairCost)
                inflatedUtils[(task.ID,costLevel)] = thisPairCost/thisPairPeriod
                if Constants.DEBUG:
                    print("task: ",task.ID, "exec level: ",costLevel, " orig cost: ", origCost, "inflated cost: ", thisPairCost)
        return inflatedUtils


    def accountForOverhead(self, taskLevel, allCritLevels, coreList, clusterList, scheme, dedicatedIRQ=False, dedicatedIRQCore=None):
        '''
        Account for overhead, for whole task system. (will not use)
        :param costLevel: execution criticality level
        :param taskCount: Number of tasks
        :param coreList: list of cores
        :param allCriticalityLevels: list of all criticality levels
        :return: A dictionary of pair -> util after accounting overheads
        '''
        #store inflated pairs. Not altering original tasks parameters. They may be needed to compare with other schedulers.
        inflatedUtils = defaultdict()

        tasksCritLevel = allCritLevels[taskLevel].tasksThisLevel
        startingTaskID = tasksCritLevel[0].ID

        if taskLevel <= Constants.LEVEL_B:
            for core in coreList:
                inflatedUtilsCore = self.accountOverheadCore(taskLevel=taskLevel, allCritLevels=allCritLevels, core=core,
                                         cacheSize=core.getAssignedCache(taskLevel), scheme=scheme,
                                         dedicatedIRQ=dedicatedIRQ, dedicatedIRQCore=dedicatedIRQCore)
                inflatedUtils.update(inflatedUtilsCore)
        else:
            for cluster in clusterList:
                inflatedUtilsCore = self.accountOverheadCluster(taskLevel = taskLevel, allCritLevels=allCritLevels,
                                                             cluster = cluster,
                                                             cacheSize = cluster.coresThisCluster[0].getAssignedCache(taskLevel),
                                                             dedicatedIRQ = dedicatedIRQ,
                                                             dedicatedIRQCore = dedicatedIRQCore)
                inflatedUtils.update(inflatedUtilsCore)
        return inflatedUtils


def main():
    overHeads = Overheads()
    overHeads.loadOverheadData('oheads')
    value = overHeads.montonicInterpolation(75,0,'CXS')
    '''task1 = Task(1,1,5,5,2)
    task2 = Task(2,1,5,5,3)
    task3 = Task(3,1,5,5,4)
    task4 = Task(4,1,5,5,1)
    task5 = Task(5,1,5,5,2)
    task6 = Task(6,1,5,5,1)
    pairs = []
    pairs.append((task1,task1))
    pairs.append((task2,task4))
    pairs.append((task3,task5))
    pairs.append((task6,task6))
    overHeads.getCPMD(1,5,pairs)
    print(value)'''
    return

if __name__== "__main__":
     main()