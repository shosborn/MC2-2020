from csv import DictReader
from collections import defaultdict
from constants import Constants
import pandas as pd
from task import Task


class Overheads:

    def __init__(self):
        self.overheadData = None
        self.overheadValue = defaultdict()
        for key in Constants.overheadTypes:
            self.overheadValue[key] = defaultdict()
            for level in range(Constants.LEVEL_A,Constants.LEVEL_C+1):
                self.overheadValue[key][level] = defaultdict()

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

    def getOverheadValue(self,taskCount,costLevel,overhead):
        '''
        get overhead value. currently for any overhead other than CPMD
        use list of tasks instead of taskCount (may be needed for CPMD)? otherwise for CPMD getCPMD() method can be called directly.
        :param taskCount: number of tasks
        :param costLevel: execution criticality level for overhead data
        :param overhead: overhead type for which value is derived
        :return:
        '''
        if overhead == 'CPMD': #cache related preemption and migration delay
            raise NotImplementedError
        # for any taskcount > max # of tasks in overhead data, maxmimum observed overhead value is used
        return self.montonicInterpolation(taskCount,costLevel,overhead)

    def getCPMD(self,pairs,tasks,taskLevel,costLevel,cacheSize):
        '''
        calculate cache related preemption and migration delay.
        wss is assumed to be stored in task.py
        todo: for level-A, -B, cachesize can be be found from its assigned core?
        :param pairs: pairs of criticality level-'taskLevel' assigned to a core/ core-complex
        :param tasks: all tasks at the criticality level-'taskLevel' (pairs criticality level)
        :param taskLevel: criticality level of pairs (not used)
        :param costLevel: criticality level of execution
        :param cacheSize: cachesize allocated to the pairs at 'taskLevel' of a core (for level-B) or core-complex (for level-C)
        :return: A pair of (taskpair,cpmdCost)
        '''
        #pairWSS = [(pair, pair[0].wss if pair[0]==pair[1] else pair[0].wss+pair[1].wss) for pair in pairs]

        pairWSS = [(pair, max(tasks[pair[0]].wss,tasks[pair[1]].wss)) for pair in pairs]
        pairWSS.sort(key=lambda tuple: tuple[1], reverse=True)
        '''for pair in pairWSS:
            print(pair[0][0].ID,pair[0][1].ID,pair[1])
        '''
        cpmd = []
        if len(pairWSS) == 1:
            if pairWSS[0][1] > cacheSize:
                cpmd.append((pairWSS[0][0],0))
            else:
                cpmd.append((pairWSS[0][0], Constants.CPMD_PER_UNIT[costLevel] * pairWSS[0][1]))
        if len(pairWSS) > 1:
            if pairWSS[1][1] > cacheSize:
                cpmd.append((pairWSS[1][0],0))
            else:
                cpmd.append((pairWSS[1][0], Constants.CPMD_PER_UNIT[costLevel] * pairWSS[1][1]))
        return cpmd

    def irqCosts(self,costLevel,dedicatedIRQ,allCriticalityLevels):
        '''
        compute values to account irq overheads
        :param costLevel: criticality level of execution
        :param dedicatedIRQ: whether dedicated irq or not
        :param allCriticalityLevels: list of all criticality level objects (since all tasks are needed here)
        :return:
        '''
        tick = self.overheadValue['tick'][costLevel] #Delta_tck
        releaseLatency = self.overheadValue['releaseLatency'][costLevel] #Delta_ev
        release = self.overheadValue['release'][costLevel] #Delta_rel
        eTick = (tick + Constants.CPI_PER_UNIT[costLevel]) #page 251
        eIrq = (release + Constants.CPI_PER_UNIT[costLevel]) #page 251
        uTick = eTick / Constants.QUANTUM_LENGTH #page 251
        uRelease = 0 #third term of denominator of Expression 3.17 (page 252)
        if dedicatedIRQ == False:
            for critLevel in allCriticalityLevels:
                for task in critLevel.tasksThisLevel:
                    uRelease += (eTick /task.period) # u^irq = (eTick /task.period), page 251

        denominator = (1- uTick - uRelease) #denominator of 3.17
        cPre = eTick + releaseLatency * uTick #first two terms of numerator of 3.18
        if dedicatedIRQ == False:
            for critLevel in allCriticalityLevels:
                for task in critLevel.tasksThisLevel:
                    cPre += releaseLatency * (eTick /task.period) + eIrq #third term of numerator of 3.18

        cPre /= denominator #3.18 complete
        return denominator,cPre

    def accountForOverhead(self,costLevel,taskCount,coreList,allCriticalityLevels):
        '''
        Account for overhead
        :param costLevel:
        :param taskCount:
        :param coreList:
        :param allCriticalityLevels:
        :return: A dictionary of pair -> (period, relDeadline, cost) after accounting overheads
        '''
        #store inflated pairs. Not altering original tasks parameters. They may be needed to compare with other schedulers.
        inflatedPairs = defaultdict()
        # get approximation of overhead values from csv file for this level
        for oheadName in Constants.overheadTypes:
            oHeadCode = Constants.overheadTypes[oheadName]
            self.overheadValue[oheadName][costLevel] = self.getOverheadValue(taskCount,costLevel,oHeadCode)
        # determine relevant parameters for irq
        denominator,cPre = self.irqCosts(costLevel,False,allCriticalityLevels)
        # ipi overhead value at this level
        ipi = self.overheadValue['ipiLatency'][costLevel]

        # get scheduling and context switch overhead assuming execution at criticality level 'level'
        schedOverhead = self.overheadValue['scheduling'][costLevel]
        contextSwitch = self.overheadValue['contextSwitch'][costLevel]

        releaseLatency = self.overheadValue['releaseLatency'][costLevel]  # Delta_ev

        smtOverhead = Constants.SMT_OVERHEAD

        #consider all tasks at or before this level
        for critLevel in range(Constants.LEVEL_A,costLevel+1):
            inflatedPairs[critLevel] = defaultdict()
            tasksThisLevel = allCriticalityLevels[critLevel].tasksThisLevel
            for core in coreList:
                #cache allocated to this core for the tasks at critLevel (for level-C, easy way to adapt is to pass list of core complex
                # instead of list of cores and having similar approach to have cache size and tasks assigned at each core complex
                cacheSize = core.getAssignedCache(critLevel)

                #get cpmd cost assuming execution at criticality level 'level' for tasks at 'critLevel' assigned to this 'core'
                #level-A has 0 CPMD due to being cyclic executing, assuming no overlapping cache like miccaiah et al. rtss'15
                #level-A's cpmd-per-unit is set at 0 at constants.py, therefore the following will work for level-A too
                cpmd = self.getCPMD(core.pairsOnCore[critLevel],tasksThisLevel,critLevel,costLevel,cacheSize)

                #costs of scheduling+ctx_switch_cpmd for the two pairs in the core having largest cpmd cost
                #smt overhead is considered similar as sched overhead
                #cost1 is used for any pair other than pair1
                #cost2 is used for pair1
                if len(cpmd) <= 1:
                    pair1, cost1 = None, 0 + 2 * (schedOverhead + contextSwitch + smtOverhead) #only one task, no cpmd
                if len(cpmd) > 1:
                    pair1, cost1 = cpmd[0][0], cpmd[0][1] + 2 * (schedOverhead + contextSwitch + smtOverhead)
                    pair2, cost2 = cpmd[1][0], cpmd[1][1] + 2 * (schedOverhead + contextSwitch + smtOverhead)

                for pair in core.pairsOnCore[critLevel]:
                    #cost assuming execution at critcality level-'level'
                    thisPairCost = tasksThisLevel[pair[0]].allUtil[(pair[1], costLevel, cacheSize)]*tasksThisLevel[pair[0]].period
                    if len(cpmd) <= 1:
                        thisPairCost += cost1
                    elif tasksThisLevel[pair[0]].ID == tasksThisLevel[pair1[0]].ID:
                        thisPairCost += cost2
                    else:
                        thisPairCost += cost1

                    thisPairCost /= denominator

                    if critLevel <= Constants.LEVEL_B:
                        thisPairCost += 2*cPre # no ipi for partitioned (page 227)
                    else:
                        thisPairCost += 2 * cPre + ipi

                    thisPairPeriod = tasksThisLevel[pair[0]].period - releaseLatency
                    thisRelDeadline = tasksThisLevel[pair[0]].relDeadline - releaseLatency

                    inflatedPairs[critLevel][pair] = (thisPairPeriod,thisRelDeadline,thisPairCost)
        return inflatedPairs

def main():
    overHeads = Overheads()
    overHeads.loadOverheadData('oheads')
    value = overHeads.montonicInterpolation(75,0,'CXS')
    task1 = Task(1,1,5,5,2)
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
    print(value)
    return

if __name__== "__main__":
     main()