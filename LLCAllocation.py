from gurobipy import *
import numpy as np
import csv
from constants import Constants

SOLO = 0
PAIRED = 1

TIMEOUT=60
SOLUTION_LIMIT=1000
THREADS_PER_TEST=0

class LLCAllocation:

    def setParam(self, solver):
        solver.setParam("TimeLimit", TIMEOUT)
        solver.setParam("SolutionLimit", SOLUTION_LIMIT)
        solver.setParam(GRB.Param.Threads, THREADS_PER_TEST)
        solver.setParam(GRB.Param.OutputFlag, 0)

    def setLevelAMinPeriods(self, taskSystem, complex):
        '''
        set level-A minimum periods for all cores in a core-complex
        :param taskSystem: task-system
        :param complex: core-complex
        :return:
        '''
        for core in complex.coreList:
            levelAPairsOnCore = core.pairsOnCore[Constants.LEVEL_A]
            # set min level-A period
            if len(levelAPairsOnCore) > 0:
                levelAAllTasks = taskSystem.levelA.tasksThisLevel
                levelAStartingIndex = levelAAllTasks[0].ID
                core.minLevelAPeriod = 999999999
                for pair in levelAPairsOnCore:
                    core.minLevelAPeriod = min(core.minLevelAPeriod, levelAAllTasks[pair[0] - levelAStartingIndex].period)

    def createIDtoIndexMap(self,complex):
        '''
        Create dictionaries which maps each coreID (clusterIDs) to the index at where it is in that complex's coreList (or ClusterList)
        :param complex: core-complex
        :return: dictionaries coreIDtoIndex and clusterIDtoIndex
        '''
        coreIDtoIndex = {}
        clusterIDtoIndex = {}
        index = 0
        for core in complex.coreList:
            coreIDtoIndex[core.coreID] = index
            index += 1

        index = 0
        for cluster in complex.clusterList:
            clusterIDtoIndex[cluster.clusterID] = index
            index += 1
        return coreIDtoIndex, clusterIDtoIndex

    def initData(self, levelABDimension, levelCDimension):
        '''
        initializes arrays for ilp data
        :param levelABDimension: dimension needed for level-A,-B tasks
        :param levelCDimension: dimension needed for level-C tasks
        :return: np arrays of total utilization data (UData), min-utilization data at level-C (hData), and sum of top m-1 utilizations data at level-C (HData)
        '''
        UData = {}

        for taskLevel in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
            for costLevel in range(taskLevel, Constants.LEVEL_C + 1):
                if taskLevel <= Constants.LEVEL_B:
                    UData[(taskLevel, costLevel)] = np.zeros(levelABDimension)
                else:
                    UData[(taskLevel, costLevel)] = np.zeros(levelCDimension)

        hData = np.zeros(levelCDimension)
        HData = np.zeros(levelCDimension)
        return  UData, hData, HData


    def coreWiseAllocation(self, taskSystem, maxWays, overheads, complex, corePerComplex, dedicatedIRQ=False, dedicatedIRQCore=None) -> int:
        '''
        :param corePerComplex: number of cores per complex
        :param maxWays:
        :param overheads:
        :param cluster:
        :param cluster2:
        :return:
        '''

        self.setLevelAMinPeriods(taskSystem,complex)

        coreIDtoIndex, clusterIDtoIndex = self.createIDtoIndexMap(complex)

        UData, hData, HData = self.initData((corePerComplex, maxWays+1), (len(complex.clusterList), maxWays + 1))
        #print(len(taskSystem.levelA.tasksThisLevel) + len(taskSystem.levelB.tasksThisLevel) + len(
        #    taskSystem.levelC.tasksThisLevel))
        for numWays in range(0, maxWays + 1):
            for core in complex.coreList:
                for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                    #1 way = 2 half way [1,1]
                    #print("core id: ", core.coreID, " pairs: ", len(core.pairsOnCore[taskLevel]), "tasklevel: ",taskLevel)
                    #utilization when this core is assigned 'numWays' full ways
                    inflatedUtil = overheads.accountOverheadCore(taskLevel=taskLevel, allCritLevels=taskSystem.levels,
                                                                 core=core, cacheSize=[numWays, numWays],
                                                                 dedicatedIRQ = dedicatedIRQ, dedicatedIRQCore = dedicatedIRQCore)

                    #print(numWays)
                    #print(inflatedUtil)

                    for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                        UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID],numWays] = \
                            sum(inflatedUtil[(pair,costLevel)] for pair in core.pairsOnCore[taskLevel])

                '''cpmdLevelAB = overheads.CPMDInflationLevelAB(core=core,
                                                             allCriticalityLevels=taskSystem.levels,
                                                             cacheSize=[numWays, numWays],
                                                             dedicatedIRQ=dedicatedIRQ,
                                                             dedicatedIRQCore=dedicatedIRQCore)

                UData[(Constants.LEVEL_A, Constants.LEVEL_B)][coreIDtoIndex[core.coreID],numWays] += cpmdLevelAB[Constants.LEVEL_B]
                UData[(Constants.LEVEL_A, Constants.LEVEL_C)][coreIDtoIndex[core.coreID],numWays] += cpmdLevelAB[Constants.LEVEL_C]'''

            #if len == 0, then initialized value is 0
            for cluster in complex.clusterList:
                inflatedUtil = overheads.accountOverheadCluster(taskLevel=Constants.LEVEL_C, allCritLevels=taskSystem.levels,
                                                                cluster = cluster,
                                                                cacheSize = numWays,
                                                                dedicatedIRQ=dedicatedIRQ,
                                                                dedicatedIRQCore=dedicatedIRQCore)
                util = sum(inflatedUtil[(task.ID, Constants.LEVEL_C)] for task in cluster.taskList)
                UData[(Constants.LEVEL_C, Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays] = util
                levelCUtilValues = list(inflatedUtil.values())
                sortedLeveCInflatedUtil = sorted(levelCUtilValues, reverse=True)

                if cluster.threaded:
                    m = 2*len(cluster.coresThisCluster)
                else:
                    m = len(cluster.coresThisCluster)
                for i in range(0, min(m - 1, len(sortedLeveCInflatedUtil))):
                    if i==0:
                        hData[clusterIDtoIndex[cluster.clusterID], numWays] = sortedLeveCInflatedUtil[i]
                    HData[clusterIDtoIndex[cluster.clusterID],numWays] += sortedLeveCInflatedUtil[i]

        if Constants.DEBUG:
            print("level a")
            print(UData[(Constants.LEVEL_A,Constants.LEVEL_A)])
            print(UData[(Constants.LEVEL_A,Constants.LEVEL_B)])
            print(UData[(Constants.LEVEL_A,Constants.LEVEL_C)])
            print("level b")
            print(UData[(Constants.LEVEL_B,Constants.LEVEL_B)])
            print(UData[(Constants.LEVEL_B,Constants.LEVEL_C)])
            print("level c")
            for cluster in complex.clusterList:
                print("cluster id: ", cluster.clusterID, " tasks: ", len(cluster.taskList), " threaded: ", cluster.threaded)
            print(UData[(Constants.LEVEL_C,Constants.LEVEL_C)])
            print("hdata")
            print(hData)
            print((HData))


        solver = Model()
        solver.setParam('OutputFlag', False)

        # create variables

        # 0 -> core1, 1 -> core2, ..., n-1 -> coren, n-> levelC
        W = [solver.addVar(lb=0, ub=maxWays, vtype=GRB.INTEGER) for core in complex.coreList] #num Ways for each core
        W.append(solver.addVar(lb=0, ub=maxWays,vtype= GRB.INTEGER)) #num Ways for level-C

        U = {}
        h = {}
        H = {}
        for taskLevel in (Constants.LEVEL_A,Constants.LEVEL_B):
            for core in complex.coreList:
                for costLevel in range(taskLevel,Constants.LEVEL_C+1):
                    U[(taskLevel,costLevel,core.coreID)] = solver.addVar(lb=0, ub=1, vtype = GRB.CONTINUOUS)

        for cluster in complex.clusterList:
            U[(Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] = solver.addVar(lb=0, vtype = GRB.CONTINUOUS)
            h[cluster.clusterID] = solver.addVar(lb=0, vtype = GRB.CONTINUOUS)
            H[cluster.clusterID] = solver.addVar(lb=0, vtype = GRB.CONTINUOUS)

        # add constraints

        # constaints set 1
        solver.addConstr(sum(W[i] for i in range(0,len(complex.coreList)+1)) <= maxWays)

        #constraints set 2
        for numWays in range(0,maxWays):
            #print(numWays)
            for core in complex.coreList:

                for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                    #print(core.coreID,len(core.pairsOnCore[taskLevel]))
                    cpmdLevelAB = overheads.CPMDInflationLevelAB(core=core,
                                                                 allCriticalityLevels=taskSystem.levels,
                                                                 cacheSize=[numWays, numWays],
                                                                 dedicatedIRQ=dedicatedIRQ,
                                                                 dedicatedIRQCore=dedicatedIRQCore)
                    for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                        x1 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], numWays]
                        x2 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], numWays+1]

                        if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and \
                                len(core.pairsOnCore[Constants.LEVEL_A]) > 0 and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                            if dedicatedIRQ and dedicatedIRQCore != core:
                                effectiveDenom = overheads.denom[False][costLevel]
                            else:
                                effectiveDenom = overheads.denom[True][costLevel]
                            # unit is half way
                            I_A_term = cpmdLevelAB[costLevel]#numWays * (Constants.CPMD_PER_UNIT[costLevel] * 2) / (effectiveDenom * core.minLevelAPeriod)

                            schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel]+overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                    effectiveDenom * core.minLevelAPeriod)
                            solver.addConstr(U[(taskLevel, costLevel, core.coreID)] - W[coreIDtoIndex[core.coreID]] * (x2 - x1)
                                                >= x1 - numWays * (x2 - x1) + I_A_term + schedCtxABterm)
                            #print(I_A_term, schedCtxABterm, "extra")
                        else:
                            solver.addConstr(U[(taskLevel,costLevel,core.coreID)] - W[coreIDtoIndex[core.coreID]] * (x2 - x1)
                                                >= x1 - numWays * (x2 - x1))
                        #print(costLevel, x1, x2)
            for cluster in complex.clusterList:
                x1 = UData[(Constants.LEVEL_C,Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID],numWays]
                x2 = UData[(Constants.LEVEL_C,Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID],numWays+1]

                solver.addConstr(U[(Constants.LEVEL_C,Constants.LEVEL_C, cluster.clusterID)] - W[-1] * (x2-x1)
                                                    >= x1 - numWays * (x2-x1))

                #constraint set 3
                x1 = hData[clusterIDtoIndex[cluster.clusterID],numWays]
                x2 = hData[clusterIDtoIndex[cluster.clusterID],numWays+1]

                solver.addConstr(h[cluster.clusterID] - W[-1] * (x2 - x1) >= x1 - numWays * (x2-x1))

                x1 = HData[clusterIDtoIndex[cluster.clusterID], numWays]
                x2 = HData[clusterIDtoIndex[cluster.clusterID], numWays + 1]

                solver.addConstr(H[cluster.clusterID] - W[-1] * (x2 - x1) >= x1 - numWays * (x2 - x1))

        #constraint set 4
        for core in complex.coreList:
            solver.addConstr(U[(Constants.LEVEL_A,Constants.LEVEL_A,core.coreID)] <= 1)
            solver.addConstr(U[(Constants.LEVEL_A,Constants.LEVEL_B,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_B,core.coreID)] <= 1)

        EPSILON = 1e-6
        for cluster in complex.clusterList:
            if cluster.threaded:
                m = 2*len(cluster.coresThisCluster)

                solver.addConstr(sum(2*U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + 2*U[(
                    Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)] for core in cluster.coresThisCluster) + U[(
                    Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] <= m)

                solver.addConstr(sum(2*U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + 2*U[
                    (Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)]
                                     for core in cluster.coresThisCluster) +
                                 (m - 1) * h[cluster.clusterID] + H[cluster.clusterID]
                                 <= m - EPSILON)
            else:
                m = len(cluster.coresThisCluster)

                solver.addConstr(sum(U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + U[(
                    Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)] for core in cluster.coresThisCluster) + U[(
                    Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] <= m)

                solver.addConstr(sum(U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + U[
                    (Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)]
                                     for core in cluster.coresThisCluster) +
                                 (m - 1) * h[cluster.clusterID] + H[cluster.clusterID]
                                 <= m - EPSILON)

            #set objective function
        solver.setObjective( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                                    for core in complex.coreList) + sum(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)]
                                       for cluster in complex.clusterList), GRB.MINIMIZE)

        self.setParam(solver)

        solver.optimize()

        if solver.status == GRB.OPTIMAL:
            #if case_study == True and iter is not None:
            for core in complex.coreList:
                size = W[coreIDtoIndex[core.coreID]].x  # size has num of ways
                core.cacheAB = [size, size]  # [halfways, halfways]
                core.cacheC = W[-1].x * 2

            '''for cluster in complex.clusterList:
                print("clusterid: ",cluster.clusterID)
                for core in cluster.coresThisCluster:
                    print("coreid: ", core.coreID)
                    print(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)].x)
                    print(U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)].x)
                print(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)].x)'''

        return solver.status


def main():
    solver = LLCAllocation()

if __name__== "__main__":
     main()
