from gurobipy import *
import numpy as np
#import pandas as pd

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


    def threadWiseAllocation2(self, taskSystem, maxWays, overheads, complex, corePerComplex, dedicatedIRQ=False, dedicatedIRQCore=None) -> int:
        '''

        :param corePerComplex: number of cores per complex
        :param maxWays:
        :param overheads:
        :param cluster:
        :param cluster2:
        :return:
        '''

        self.setLevelAMinPeriods(taskSystem, complex)

        coreIDtoIndex, clusterIDtoIndex = self.createIDtoIndexMap(complex)

        UData = {}

        for taskLevel in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
            for costLevel in range(taskLevel, Constants.LEVEL_C + 1):
                if taskLevel <= Constants.LEVEL_B:
                    UData[(taskLevel, costLevel, SOLO)] = np.zeros((corePerComplex, (maxWays+1)))
                    UData[(taskLevel, costLevel, PAIRED)] = np.zeros((corePerComplex, (maxWays+1), (maxWays+1)))
                else:
                    UData[(taskLevel, costLevel)] = np.zeros((len(complex.clusterList), (maxWays + 1)))

        hData = np.zeros((len(complex.clusterList), (maxWays + 1)))
        HData = np.zeros((len(complex.clusterList), (maxWays + 1)))

        for thread1Ways in range(0, maxWays + 1):
            for thread2Ways in range(0, maxWays + 1):
                for core in complex.coreList:
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        #1 way = 2 half way [1,1]
                        #print("core id: ", core.coreID, " pairs: ", len(core.pairsOnCore[taskLevel]), "tasklevel: ",taskLevel)
                        inflatedUtil = overheads.accountOverheadCore(taskLevel=taskLevel, allCritLevels=taskSystem.levels,
                                                                     core=core, cacheSize=[thread1Ways, thread2Ways],
                                                                     dedicatedIRQ = dedicatedIRQ, dedicatedIRQCore = dedicatedIRQCore)

                        #print(numWays)
                        #print(inflatedUtil)

                        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                            #utilization at this core when allocated halfways of 'thread1Way' and 'thread2Way'
                            soloUtil = 0
                            pairedUtil = 0
                            for pair in core.pairsOnCore[taskLevel]:
                                if pair[0] == pair[1]:
                                    soloUtil += inflatedUtil[(pair,costLevel)]
                                else:
                                    pairedUtil += inflatedUtil[(pair,costLevel)]
                            UData[(taskLevel, costLevel, SOLO)][coreIDtoIndex[core.coreID], min(thread1Ways, thread2Ways)] = \
                                            max(soloUtil, UData[(taskLevel, costLevel, SOLO)][coreIDtoIndex[core.coreID], min(thread1Ways, thread2Ways)])
                            UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways] = pairedUtil

        for numWays in range(0, maxWays + 1):
            for cluster in complex.clusterList:
                #generate util considering level-C allocated 'thread1way' number of full ways.
                inflatedUtil = overheads.accountOverheadCluster(taskLevel=Constants.LEVEL_C, allCritLevels=taskSystem.levels,
                                                                cluster = cluster,
                                                                cacheSize = numWays, #no of half ways
                                                                dedicatedIRQ=dedicatedIRQ,
                                                                dedicatedIRQCore=dedicatedIRQCore)
                util = sum(inflatedUtil[(task.ID, Constants.LEVEL_C)] for task in cluster.taskList)

                # utilization at this cluster when allocated full ways of 'thread1Way'
                UData[(Constants.LEVEL_C, Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays] = util
                levelCUtilValues = list(inflatedUtil.values())
                sortedLeveCInflatedUtil = sorted(levelCUtilValues, reverse=True)

                HData[clusterIDtoIndex[cluster.clusterID], numWays] = 0
                m = len(cluster.coresThisCluster)
                for i in range(0, min(m - 1, len(sortedLeveCInflatedUtil))):
                    if i==0:
                        hData[clusterIDtoIndex[cluster.clusterID], numWays] = sortedLeveCInflatedUtil[i]
                    HData[clusterIDtoIndex[cluster.clusterID], numWays] += sortedLeveCInflatedUtil[i]

        '''if Constants.DEBUG:
            print(UData[(Constants.LEVEL_A, Constants.LEVEL_A, PAIRED)])
            print(UData[(Constants.LEVEL_A, Constants.LEVEL_A, SOLO)])
            print(UData[(Constants.LEVEL_A, Constants.LEVEL_B, PAIRED)])
            print(UData[(Constants.LEVEL_A, Constants.LEVEL_B, SOLO)])
            print(UData[(Constants.LEVEL_A, Constants.LEVEL_C, PAIRED)])
            print(UData[(Constants.LEVEL_A, Constants.LEVEL_C, SOLO)])
            print(UData[(Constants.LEVEL_B, Constants.LEVEL_B, PAIRED)])
            print(UData[(Constants.LEVEL_B, Constants.LEVEL_B, SOLO)])
            print(UData[(Constants.LEVEL_B, Constants.LEVEL_C)])
            print(UData[(Constants.LEVEL_C, Constants.LEVEL_C)])
            print(hData)
            print(HData)'''


        solver = Model()

        # create variables

        numCores = len(complex.coreList)
        numThreads = 2 * numCores

        # 0 -> core1, 1 -> core2, ..., n-1 -> coren, n-> levelC
        W = [solver.addVar(lb=0, ub=maxWays, vtype=GRB.INTEGER) for i in range(0,numThreads)] #num of Ways for each thread
        W.append(solver.addVar(lb=0, ub=maxWays, vtype= GRB.INTEGER)) #num Ways for level-C

        U = {}
        h = {}
        H = {}
        for taskLevel in (Constants.LEVEL_A,Constants.LEVEL_B):
            for core in complex.coreList:
                for costLevel in range(taskLevel,Constants.LEVEL_C+1):
                    U[(taskLevel,costLevel,core.coreID)] = solver.addVar(lb=0, ub=1, vtype = GRB.CONTINUOUS)
                    if taskLevel <= Constants.LEVEL_B:
                        U[(taskLevel, costLevel, core.coreID, SOLO)] = solver.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS)
                        U[(taskLevel, costLevel, core.coreID, PAIRED)] = solver.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS)
                        #print((taskLevel, costLevel, core.coreID, SOLO), (taskLevel, costLevel, core.coreID, PAIRED))

        for cluster in complex.clusterList:
            U[(Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] = solver.addVar(lb=0, vtype = GRB.CONTINUOUS)
            h[cluster.clusterID] = solver.addVar(lb=0, vtype = GRB.CONTINUOUS)
            H[cluster.clusterID] = solver.addVar(lb=0, vtype = GRB.CONTINUOUS)

        # add constraints

        # constaints set 1

        #i and m+i are half ways allocated to same core's threads
        #numThread indexed -> level C full ways
        # 0 to m-1 -> color 0
        # m to 2m-1 -> color 1
        solver.addConstr(sum(W[i] for i in range(0,numCores)) + W[numThreads] <= maxWays)
        solver.addConstr(sum(W[i] for i in range(numCores,numThreads)) + W[numThreads] <= maxWays)

        #constraints set 2

        for numWays in range(0, maxWays):
            for core in complex.coreList:
                for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                    for costLevel in range(taskLevel, Constants.LEVEL_C+1):

                        u1 = UData[(taskLevel,costLevel,SOLO)][coreIDtoIndex[core.coreID], numWays]
                        u2 = UData[(taskLevel,costLevel,SOLO)][coreIDtoIndex[core.coreID], numWays+1]
                        I_A_term = 0
                        if len(core.pairsOnCore[Constants.LEVEL_A]) > 0 and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                            if dedicatedIRQ and dedicatedIRQCore != core:
                                effectiveDenom = overheads.denom[False][costLevel]
                            else:
                                effectiveDenom = overheads.denom[True][costLevel]
                            I_A_term = numWays * (Constants.CPMD_PER_UNIT[costLevel] * 2) / (
                                    effectiveDenom * core.minLevelAPeriod)

                        solver.addConstr(U[(taskLevel, costLevel, core.coreID, SOLO)] - W[coreIDtoIndex[core.coreID]] * (u2-u1)
                                                            >= u1 - numWays * (u2-u1) + I_A_term)
                        solver.addConstr(U[(taskLevel, costLevel, core.coreID, SOLO)] - W[coreIDtoIndex[core.coreID] + numCores ] * (u2-u1)
                                                            >= u1 - numWays * (u2-u1)+I_A_term)


        for thread1Ways in range(0, maxWays):
            for thread2Ways in range(0, maxWays):
                for core in complex.coreList:
                    coreID = core.coreID
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                            '''
                            approximate ax+by+zu = d using three points in space
                            util->u for x->ways to thread 1 and y->ways to thread 2
                            three points p1(x1, y1, u1), p2(x1+1, y1, u2), and p3(x1, y1+1, u3)'
                            '''
                            u1 = UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways]
                            u2 = UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways+1, thread2Ways]
                            u3 = UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways+1]

                            factor1 = u2 - u1
                            factor2 = u3 - u1

                            wVarThread1 = W[coreIDtoIndex[coreID]]
                            wVarThread2 = W[coreIDtoIndex[coreID] + numCores]

                            if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and \
                                    len(core.pairsOnCore[Constants.LEVEL_A]) > 0 and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                                if dedicatedIRQ and dedicatedIRQCore != core:
                                    effectiveDenom = overheads.denom[False][costLevel]
                                else:
                                    effectiveDenom = overheads.denom[True][costLevel]
                                # unit is half way
                                I_A_term = (thread1Ways + thread2Ways) * ( Constants.CPMD_PER_UNIT[costLevel] * 2 ) / (effectiveDenom * core.minLevelAPeriod)
                                solver.addConstr(U[(taskLevel, costLevel, coreID, PAIRED)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2
                                                        + I_A_term)
                            else:
                                solver.addConstr(U[(taskLevel, costLevel, coreID, PAIRED)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2)


        for thread1Ways in range(1, maxWays+1):
            for thread2Ways in range(1, maxWays+1):
                for core in complex.coreList:
                    coreID = core.coreID
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                            '''
                            approximate ax+by+zu = d using three points in space
                            util->u for x->ways to thread 1 and y->ways to thread 2
                            three points p1(x1, y1, u1), p2(x1-1, y1, u2), and p3(x1, y1-1, u3)'
                            '''
                            u1 = UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways]
                            u2 = UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways-1, thread2Ways]
                            u3 = UData[(taskLevel, costLevel, PAIRED)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways-1]

                            factor1 = u1 - u2
                            factor2 = u1 - u3

                            wVarThread1 = W[coreIDtoIndex[coreID]]
                            wVarThread2 = W[coreIDtoIndex[coreID] + numCores]

                            if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and \
                                    len(core.pairsOnCore[Constants.LEVEL_A]) > 0 and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                                if dedicatedIRQ and dedicatedIRQCore != core:
                                    effectiveDenom = overheads.denom[False][costLevel]
                                else:
                                    effectiveDenom = overheads.denom[True][costLevel]
                                # unit is half way
                                I_A_term = (thread1Ways + thread2Ways) * ( Constants.CPMD_PER_UNIT[costLevel] * 2 ) / (effectiveDenom * core.minLevelAPeriod)
                                solver.addConstr(U[(taskLevel, costLevel, coreID, PAIRED)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2
                                                        + I_A_term)
                            else:
                                solver.addConstr(U[(taskLevel, costLevel, coreID, PAIRED)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2)

        for core in complex.coreList:
            for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                    schedCtxABterm = 0
                    if len(core.pairsOnCore[Constants.LEVEL_A])>0 and len(core.pairsOnCore[Constants.LEVEL_B])>0:
                        if dedicatedIRQ and dedicatedIRQCore != core:
                            effectiveDenom = overheads.denom[False][costLevel]
                        else:
                            effectiveDenom = overheads.denom[True][costLevel]
                        schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel] +
                                          overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                 effectiveDenom * core.minLevelAPeriod)
                    solver.addConstr(U[(taskLevel,costLevel,core.coreID)] >= U[(taskLevel,costLevel,core.coreID,SOLO)] +
                                     U[(taskLevel,costLevel,core.coreID,PAIRED)]+schedCtxABterm)

        for numWays in range(0, maxWays):
            for cluster in complex.clusterList:
                #thread1Way = ways allocated to level-C (not splitted between threads)
                u1 = UData[(Constants.LEVEL_C,Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays]
                u2 = UData[(Constants.LEVEL_C,Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays+1]

                solver.addConstr(U[(Constants.LEVEL_C,Constants.LEVEL_C, cluster.clusterID)] - W[-1] * (u2-u1)
                                                    >= u1 - numWays * (u2-u1))

                #constraint set 3
                u1 = hData[clusterIDtoIndex[cluster.clusterID], numWays]
                u2 = hData[clusterIDtoIndex[cluster.clusterID], numWays+1]

                solver.addConstr(h[cluster.clusterID] - W[-1] * (u2 - u1) >= u1 - numWays * (u2-u1))

                u1 = HData[clusterIDtoIndex[cluster.clusterID], numWays]
                u2 = HData[clusterIDtoIndex[cluster.clusterID], numWays + 1]

                solver.addConstr(H[cluster.clusterID] - W[-1] * (u2 - u1) >= u1 - numWays * (u2 - u1))

        #constraint set 4
        for core in complex.coreList:
            solver.addConstr(U[(Constants.LEVEL_A,Constants.LEVEL_A,core.coreID)] <= 1)
            solver.addConstr(U[(Constants.LEVEL_A,Constants.LEVEL_B,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_B,core.coreID)] <= 1)

        EPSILON = 1e-6
        for cluster in complex.clusterList:
            m = len(cluster.coresThisCluster)

            solver.addConstr(sum(U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + U[
                (Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)] for core in cluster.coresThisCluster) + U[
                (Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] <= m)

            solver.addConstr( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                              for core in cluster.coresThisCluster) +
                              (m-1) * h[cluster.clusterID] +  H[cluster.clusterID]
                              <= m - EPSILON )

            #set objective function
        solver.setObjective( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                                    for core in complex.coreList) + sum(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)]
                                       for cluster in complex.clusterList), GRB.MINIMIZE)


        self.setParam(solver)

        solver.optimize()




        if solver.status == GRB.OPTIMAL:

            for core in complex.coreList:
                size1 = W[coreIDtoIndex[core.coreID]].x #size has num of ways
                size2 = W[coreIDtoIndex[core.coreID]+numCores].x #size has num of ways
                core.cacheAB = [size1, size2] #[halfways, halfways]
                core.cacheC = W[-1].x * 2
                print(core.coreID, core.cacheAB, core.cacheC)
            print("result is: ", solver.objVal)
            sum1 = sum(W[i].x for i in range(0, numCores)) + W[-1].x
            sum2 = (sum(W[i].x for i in range(numCores, len(W))))
            '''print("sum of ways: ", sum1)
            print("sum of ways: ", sum2)
            for i in range(0, len(W)):
                print(W[i].x)'''
            '''if sum1 != maxWays or sum2 != maxWays:
                for cluster in complex.clusterList:
                    for core in cluster.coresThisCluster:
                        print("core id: ", core.coreID)
                        thread1Cache = int(W[coreIDtoIndex[core.coreID]].x)
                        thread2Cache = int(W[coreIDtoIndex[core.coreID]+numCores].x)
                        print("level A-C: ")
                        print(UData[(Constants.LEVEL_A, Constants.LEVEL_C)][coreIDtoIndex[core.coreID], thread1Cache, thread2Cache])
                        print(UData[(Constants.LEVEL_A, Constants.LEVEL_C)][coreIDtoIndex[core.coreID], thread1Cache+1, thread2Cache])
                        print(UData[(Constants.LEVEL_A, Constants.LEVEL_C)][coreIDtoIndex[core.coreID], thread1Cache, thread2Cache+1])
                        print("level B-C: ")
                        print(UData[(Constants.LEVEL_B, Constants.LEVEL_C)][
                                  coreIDtoIndex[core.coreID], thread1Cache, thread2Cache])
                        print(UData[(Constants.LEVEL_B, Constants.LEVEL_C)][
                                  coreIDtoIndex[core.coreID], thread1Cache + 1, thread2Cache])
                        print(UData[(Constants.LEVEL_B, Constants.LEVEL_C)][
                                  coreIDtoIndex[core.coreID], thread1Cache, thread2Cache + 1])
                    print("level C-C: ")

                    print(UData[(Constants.LEVEL_C, Constants.LEVEL_C)][
                                  clusterIDtoIndex[clusterIDtoIndex[cluster.clusterID]], int(W[-1].x)])'''

            #assert sum1 == sum2 == maxWays
            '''print()
            for cluster in complex.clusterList:
                print("clusterid: ",cluster.clusterID)
                for core in cluster.coresThisCluster:
                    print("coreid: ", core.coreID)
                    print(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)].x)
                    print(U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)].x)
                print(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)].x)
            '''

        for cluster in complex.clusterList:
            util = {}
            util[(Constants.LEVEL_C, Constants.LEVEL_C)] = 0
            print("cluster: ", cluster.clusterID)
            for core in cluster.coresThisCluster:
                util[(Constants.LEVEL_A,Constants.LEVEL_A)] = 0
                util[(Constants.LEVEL_A,Constants.LEVEL_B)] = 0
                util[(Constants.LEVEL_A,Constants.LEVEL_C)] = 0
                util[(Constants.LEVEL_B,Constants.LEVEL_B)] = 0
                util[(Constants.LEVEL_B,Constants.LEVEL_C)] = 0
                print("core id: ", core.coreID)
                for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                    tasksThisLevel = taskSystem.levels[taskLevel].tasksThisLevel
                    startingIndex = tasksThisLevel[0].ID
                    for pair in core.pairsOnCore[taskLevel]:
                        for costLevel in range(taskLevel,Constants.LEVEL_B+1):
                            if pair[0]!=pair[1]:
                                util[(taskLevel,costLevel)] += tasksThisLevel[pair[0]-startingIndex].allUtil[(pair[1],costLevel,min(core.cacheAB)*2)]
                            else:
                                util[(taskLevel, costLevel)] += tasksThisLevel[pair[0] - startingIndex].allUtil[
                                    (pair[1], costLevel, core.cacheAB[0]+core.cacheAB[1])]
                print("core id: ", core.coreID)
                print(" level A util: ", util[(Constants.LEVEL_A,Constants.LEVEL_A)])
                print(" level B util: ", util[Constants.LEVEL_A,Constants.LEVEL_B]+util[(Constants.LEVEL_B,Constants.LEVEL_B)])

            for task in cluster.taskList:
                if cluster.threaded:
                    thisPairUtil = 0
                    for otherTask in cluster.taskList:
                        if task != otherTask:
                            thisPairUtil = max(thisPairUtil, task.allUtil[(otherTask.ID, Constants.LEVEL_C, cluster.coresThisCluster[0].cacheC)])
                    util[(Constants.LEVEL_C,Constants.LEVEL_C)] += thisPairUtil
                else:
                    util[(Constants.LEVEL_C,Constants.LEVEL_C)] += task.allUtil[(task.ID, Constants.LEVEL_C, cluster.coresThisCluster[0].cacheC)]
            print("cluster util: ", util[(Constants.LEVEL_A,Constants.LEVEL_C)]+util[(Constants.LEVEL_B,Constants.LEVEL_C)]+util[(Constants.LEVEL_C,Constants.LEVEL_C)])


        return solver.status


    def threadWiseAllocation(self, taskSystem, maxWays, overheads, complex, corePerComplex, dedicatedIRQ=False, dedicatedIRQCore=None) -> int:
        """

        :param dedicatedIRQCore:
        :param dedicatedIRQ:
        :param complex:
        :param corePerComplex: number of cores per complex
        :param maxWays:
        :param overheads:
        :return:
        """

        self.setLevelAMinPeriods(taskSystem, complex)

        coreIDtoIndex, clusterIDtoIndex = self.createIDtoIndexMap(complex)

        UData, hData, HData = self.initData((corePerComplex, (maxWays+1), (maxWays+1)), (len(complex.clusterList), (maxWays + 1)))

        for thread1Ways in range(0, maxWays + 1):
            for thread2Ways in range(0, maxWays + 1):
                for core in complex.coreList:
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        #1 way = 2 half way [1,1]
                        #print("core id: ", core.coreID, " pairs: ", len(core.pairsOnCore[taskLevel]), "tasklevel: ",taskLevel)
                        inflatedUtil = overheads.accountOverheadCore(taskLevel=taskLevel, allCritLevels=taskSystem.levels,
                                                                     core=core, cacheSize=[thread1Ways, thread2Ways],
                                                                     dedicatedIRQ = dedicatedIRQ, dedicatedIRQCore = dedicatedIRQCore)

                        #print(numWays)
                        #print(inflatedUtil)

                        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                            #utilization at this core when allocated halfways of 'thread1Way' and 'thread2Way'
                            UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways] = \
                                sum(inflatedUtil[(pair,costLevel)] for pair in core.pairsOnCore[taskLevel])


                    cpmdLevelAB = overheads.CPMDInflationLevelAB(core=core,
                                                                 allCriticalityLevels=taskSystem.levels,
                                                                 cacheSize=[thread1Ways, thread2Ways],
                                                                 dedicatedIRQ=dedicatedIRQ,
                                                                 dedicatedIRQCore=dedicatedIRQCore)

                    UData[(Constants.LEVEL_A, Constants.LEVEL_B)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways] += cpmdLevelAB[Constants.LEVEL_B]
                    UData[(Constants.LEVEL_A, Constants.LEVEL_C)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways] += cpmdLevelAB[Constants.LEVEL_C]

        for numWays in range(0, maxWays + 1):
            for cluster in complex.clusterList:
                #generate util considering level-C allocated 'thread1way' number of full ways.
                inflatedUtil = overheads.accountOverheadCluster(taskLevel=Constants.LEVEL_C, allCritLevels=taskSystem.levels,
                                                                cluster = cluster,
                                                                cacheSize = numWays,
                                                                dedicatedIRQ=dedicatedIRQ,
                                                                dedicatedIRQCore=dedicatedIRQCore)
                util = sum(inflatedUtil[(task.ID, Constants.LEVEL_C)] for task in cluster.taskList)

                # utilization at this cluster when allocated full ways of 'thread1Way'
                UData[(Constants.LEVEL_C, Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays] = util
                levelCUtilValues = list(inflatedUtil.values())
                sortedLeveCInflatedUtil = sorted(levelCUtilValues, reverse=True)

                HData[clusterIDtoIndex[cluster.clusterID], numWays] = 0
                m = len(cluster.coresThisCluster)
                for i in range(0, min(m - 1, len(sortedLeveCInflatedUtil))):
                    if i==0:
                        hData[clusterIDtoIndex[cluster.clusterID], numWays] = sortedLeveCInflatedUtil[i]
                    HData[clusterIDtoIndex[cluster.clusterID], numWays] += sortedLeveCInflatedUtil[i]

        #if Constants.DEBUG:
        #    print(UData[(Constants.LEVEL_A, Constants.LEVEL_A)])
        #    print(UData[(Constants.LEVEL_A, Constants.LEVEL_B)])
        #    print(UData[(Constants.LEVEL_A, Constants.LEVEL_C)])
        #    print(UData[(Constants.LEVEL_B, Constants.LEVEL_B)])
        #    print(UData[(Constants.LEVEL_B, Constants.LEVEL_C)])
        #    print(UData[(Constants.LEVEL_C, Constants.LEVEL_C)])
        #    print(hData)
        #    print((HData))


        solver = Model()
        solver.setParam('OutputFlag', False)

        # create variables

        numCores = len(complex.coreList)
        numThreads = 2 * numCores

        # 0 -> core1, 1 -> core2, ..., n-1 -> coren, n-> levelC
        W = [solver.addVar(lb=0, ub=maxWays, vtype=GRB.INTEGER) for i in range(0,numThreads)] #num of Ways for each thread
        W.append(solver.addVar(lb=0, ub=maxWays, vtype= GRB.INTEGER)) #num Ways for level-C

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

        #i and m+i are half ways allocated to same core's threads
        #numThread indexed -> level C full ways
        # 0 to m-1 -> color 0
        # m to 2m-1 -> color 1
        solver.addConstr(sum(W[i] for i in range(0,numCores)) + W[numThreads] <= maxWays)
        solver.addConstr(sum(W[i] for i in range(numCores,numThreads)) + W[numThreads] <= maxWays)

        #constraints set 2


        for thread1Ways in range(0, maxWays):
            for thread2Ways in range(0, maxWays):
                for core in complex.coreList:
                    coreID = core.coreID
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        for costLevel in range(taskLevel, Constants.LEVEL_C + 1):
                            '''
                            approximate ax+by+zu = d using three points in space
                            util->u for x->ways to thread 1 and y->ways to thread 2
                            three points p1(x1, y1, u1), p2(x1+1, y1, u2), and p3(x1, y1+1, u3)
                            vector r12 = (1, 0, u2-u1), r13 = (0, 1, u3-u1)
                            normal vector = (u1-u2, u1-u3, 1)
                            so, a=(u1-u2), b=(u1-u3), c=1
                            d = (u1-u2)x1 + b(u1-u3)y1 + u1, plugging p1
                            (u1-u2)x + (u1-u3)y + u = u1 + (u1-u2)x1 + b(u1-u3)y1
                            rearranging, u = u1 + (u2-u1)(x-x1) + (u3-u1)(y-y1)
                            '''
                            u1 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways]
                            u2 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways + 1, thread2Ways]
                            u3 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways + 1]

                            factor1 = u2 - u1
                            factor2 = u3 - u1

                            wVarThread1 = W[coreIDtoIndex[coreID]]
                            wVarThread2 = W[coreIDtoIndex[coreID] + numCores]

                            if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and len(
                                    core.pairsOnCore[Constants.LEVEL_A]) > 0 and len(
                                    core.pairsOnCore[Constants.LEVEL_B]) > 0:
                                if dedicatedIRQ and dedicatedIRQCore != core:
                                    effectiveDenom = overheads.denom[False][costLevel]
                                else:
                                    effectiveDenom = overheads.denom[True][costLevel]
                                # unit is half way
                                I_A_term = (thread1Ways + thread2Ways) * (Constants.CPMD_PER_UNIT[costLevel] * 2) / (
                                            effectiveDenom * core.minLevelAPeriod)
                                schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel] +
                                                  overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                         effectiveDenom * core.minLevelAPeriod)
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                 - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2
                                                 + I_A_term + schedCtxABterm)
                            else:
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                 - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2)

        for thread1Ways in range(1, maxWays + 1):
            for thread2Ways in range(1, maxWays + 1):
                for core in complex.coreList:
                    coreID = core.coreID
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        for costLevel in range(taskLevel, Constants.LEVEL_C + 1):
                            '''
                            approximate ax+by+zu = d using three points in space
                            util->u for x->ways to thread 1 and y->ways to thread 2
                            three points p1(x1, y1, u1), p2(x1-1, y1, u2), and p3(x1, y1-1, u3)'
                            '''
                            u1 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways]
                            u2 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways - 1, thread2Ways]
                            u3 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways - 1]

                            factor1 = u1 - u2
                            factor2 = u1 - u3

                            wVarThread1 = W[coreIDtoIndex[coreID]]
                            wVarThread2 = W[coreIDtoIndex[coreID] + numCores]

                            if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and len(
                                    core.pairsOnCore[Constants.LEVEL_A]) > 0 and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                                if dedicatedIRQ and dedicatedIRQCore != core:
                                    effectiveDenom = overheads.denom[False][costLevel]
                                else:
                                    effectiveDenom = overheads.denom[True][costLevel]
                                # unit is half way
                                I_A_term = (thread1Ways + thread2Ways) * (Constants.CPMD_PER_UNIT[costLevel] * 2) / (
                                            effectiveDenom * core.minLevelAPeriod)
                                schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel] +
                                                  overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                         effectiveDenom * core.minLevelAPeriod)
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                 - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2
                                                 + I_A_term + schedCtxABterm)
                            else:
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                 - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2)

        for thread1Ways in range(1, maxWays+1):
            for thread2Ways in range(0, maxWays):
                for core in complex.coreList:
                    coreID = core.coreID
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                            '''
                            approximate ax+by+zu = d using three points in space
                            util->u for x->ways to thread 1 and y->ways to thread 2
                            three points p1(x1, y1, u1), p2(x1-1, y1, u2), and p3(x1, y1+1, u3)'
                            '''
                            u1 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways]
                            u2 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways-1, thread2Ways]
                            u3 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways+1]

                            factor1 = u1 - u2
                            factor2 = u3 - u1

                            wVarThread1 = W[coreIDtoIndex[coreID]]
                            wVarThread2 = W[coreIDtoIndex[coreID] + numCores]

                            if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and len(core.pairsOnCore[Constants.LEVEL_A]) > 0\
                                    and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                                if dedicatedIRQ and dedicatedIRQCore != core:
                                    effectiveDenom = overheads.denom[False][costLevel]
                                else:
                                    effectiveDenom = overheads.denom[True][costLevel]
                                # unit is half way
                                I_A_term = (thread1Ways + thread2Ways) * ( Constants.CPMD_PER_UNIT[costLevel] * 2 ) / (effectiveDenom * core.minLevelAPeriod)
                                schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel] +
                                                  overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                         effectiveDenom * core.minLevelAPeriod)
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2
                                                        + I_A_term + schedCtxABterm)
                            else:
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2)

        for thread1Ways in range(0, maxWays):
            for thread2Ways in range(1, maxWays+1):
                for core in complex.coreList:
                    coreID = core.coreID
                    for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                        for costLevel in range(taskLevel, Constants.LEVEL_C+1):
                            '''
                            approximate ax+by+zu = d using three points in space
                            util->u for x->ways to thread 1 and y->ways to thread 2
                            three points p1(x1, y1, u1), p2(x1+1, y1, u2), and p3(x1, y1-1, u3)'
                            '''
                            u1 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways]
                            u2 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways+1, thread2Ways]
                            u3 = UData[(taskLevel, costLevel)][coreIDtoIndex[core.coreID], thread1Ways, thread2Ways-1]

                            factor1 = u2 - u1
                            factor2 = u1 - u3

                            wVarThread1 = W[coreIDtoIndex[coreID]]
                            wVarThread2 = W[coreIDtoIndex[coreID] + numCores]

                            if taskLevel == Constants.LEVEL_A and costLevel >= Constants.LEVEL_B and len(
                                    core.pairsOnCore[Constants.LEVEL_A]) > 0 \
                                    and len(core.pairsOnCore[Constants.LEVEL_B]) > 0:
                                if dedicatedIRQ and dedicatedIRQCore != core:
                                    effectiveDenom = overheads.denom[False][costLevel]
                                else:
                                    effectiveDenom = overheads.denom[True][costLevel]
                                # unit is half way
                                I_A_term = (thread1Ways + thread2Ways) * (Constants.CPMD_PER_UNIT[costLevel] * 2) / (
                                            effectiveDenom * core.minLevelAPeriod)
                                schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel] +
                                                  overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                         effectiveDenom * core.minLevelAPeriod)
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2
                                                        + I_A_term + schedCtxABterm)
                            else:
                                solver.addConstr(U[(taskLevel, costLevel, coreID)] - wVarThread1 * factor1
                                                    - wVarThread2 * factor2 >= u1 - thread1Ways * factor1 - thread2Ways * factor2)

        for numWays in range(0, maxWays):
            for cluster in complex.clusterList:
                #thread1Way = ways allocated to level-C (not splitted between threads)
                u1 = UData[(Constants.LEVEL_C,Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays]
                u2 = UData[(Constants.LEVEL_C,Constants.LEVEL_C)][clusterIDtoIndex[cluster.clusterID], numWays+1]

                solver.addConstr(U[(Constants.LEVEL_C,Constants.LEVEL_C, cluster.clusterID)] - W[-1] * (u2-u1)
                                                    >= u1 - numWays * (u2-u1))

                #constraint set 3
                u1 = hData[clusterIDtoIndex[cluster.clusterID], numWays]
                u2 = hData[clusterIDtoIndex[cluster.clusterID], numWays+1]

                solver.addConstr(h[cluster.clusterID] - W[-1] * (u2 - u1) >= u1 - numWays * (u2-u1))

                u1 = HData[clusterIDtoIndex[cluster.clusterID], numWays]
                u2 = HData[clusterIDtoIndex[cluster.clusterID], numWays + 1]

                solver.addConstr(H[cluster.clusterID] - W[-1] * (u2 - u1) >= u1 - numWays * (u2 - u1))

        #constraint set 4
        for core in complex.coreList:
            solver.addConstr(U[(Constants.LEVEL_A,Constants.LEVEL_A,core.coreID)] <= 1)
            solver.addConstr(U[(Constants.LEVEL_A,Constants.LEVEL_B,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_B,core.coreID)] <= 1)

        EPSILON = 1e-6
        for cluster in complex.clusterList:
            m = len(cluster.coresThisCluster)

            solver.addConstr(sum(U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + U[(
                                Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)] for core in cluster.coresThisCluster) + U[(
                                    Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] <= m)

            solver.addConstr( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                              for core in cluster.coresThisCluster) +
                              (m-1) * h[cluster.clusterID] +  H[cluster.clusterID]
                              <= m - EPSILON )

            #set objective function
        solver.setObjective( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                                    for core in complex.coreList) + sum(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)]
                                       for cluster in complex.clusterList), GRB.MINIMIZE)


        self.setParam(solver)

        solver.optimize()

        if solver.status == GRB.OPTIMAL:

            for core in complex.coreList:
                size1 = W[coreIDtoIndex[core.coreID]].x #size has num of ways
                size2 = W[coreIDtoIndex[core.coreID]+numCores].x #size has num of ways
                core.cacheAB = [size1, size2] #[halfways, halfways]
                core.cacheC = W[-1].x * 2
                if Constants.DEBUG:
                    print(core.coreID, core.cacheAB, core.cacheC)

            '''print()
            for cluster in complex.clusterList:
                print("clusterid: ",cluster.clusterID)
                for core in cluster.coresThisCluster:
                    print("coreid: ", core.coreID)
                    print(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)].x)
                    print(U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)].x)
                print(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)].x)
            '''

        '''for cluster in complex.clusterList:
            util = {}
            util[(Constants.LEVEL_C, Constants.LEVEL_C)] = 0
            print("cluster: ", cluster.clusterID)
            for core in cluster.coresThisCluster:
                util[(Constants.LEVEL_A,Constants.LEVEL_A)] = 0
                util[(Constants.LEVEL_A,Constants.LEVEL_B)] = 0
                util[(Constants.LEVEL_A,Constants.LEVEL_C)] = 0
                util[(Constants.LEVEL_B,Constants.LEVEL_B)] = 0
                util[(Constants.LEVEL_B,Constants.LEVEL_C)] = 0
                print("core id: ", core.coreID)
                for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
                    tasksThisLevel = taskSystem.levels[taskLevel].tasksThisLevel
                    startingIndex = tasksThisLevel[0].ID
                    for pair in core.pairsOnCore[taskLevel]:
                        for costLevel in range(taskLevel,Constants.LEVEL_B+1):
                            if pair[0]!=pair[1]:
                                util[(taskLevel,costLevel)] += tasksThisLevel[pair[0]-startingIndex].allUtil[(pair[1],costLevel,min(core.cacheAB)*2)]
                            else:
                                util[(taskLevel, costLevel)] += tasksThisLevel[pair[0] - startingIndex].allUtil[
                                    (pair[1], costLevel, core.cacheAB[0]+core.cacheAB[1])]
                print("core id: ", core.coreID)
                print(" level A util: ", util[(Constants.LEVEL_A,Constants.LEVEL_A)])
                print(" level B util: ", util[Constants.LEVEL_A,Constants.LEVEL_B]+util[(Constants.LEVEL_B,Constants.LEVEL_B)])

            for task in cluster.taskList:
                if cluster.threaded:
                    thisPairUtil = 0
                    for otherTask in cluster.taskList:
                        if task != otherTask:
                            thisPairUtil = max(thisPairUtil, task.allUtil[(otherTask.ID, Constants.LEVEL_C, cluster.coresThisCluster[0].cacheC)])
                    util[(Constants.LEVEL_C,Constants.LEVEL_C)] += thisPairUtil
                else:
                    util[(Constants.LEVEL_C,Constants.LEVEL_C)] += task.allUtil[(task.ID, Constants.LEVEL_C, cluster.coresThisCluster[0].cacheC)]
            print("cluster util: ", util[(Constants.LEVEL_A,Constants.LEVEL_C)]+util[(Constants.LEVEL_B,Constants.LEVEL_C)]+util[(Constants.LEVEL_C,Constants.LEVEL_C)])
            '''

        return solver.status


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
            for core in complex.coreList:

                for taskLevel in (Constants.LEVEL_A, Constants.LEVEL_B):
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
                            I_A_term = numWays * (Constants.CPMD_PER_UNIT[costLevel] * 2) / (effectiveDenom * core.minLevelAPeriod)
                            schedCtxABterm = (overheads.overheadValue['scheduling'][costLevel]+overheads.overheadValue['contextSwitch'][costLevel]) / (
                                                    effectiveDenom * core.minLevelAPeriod)
                            solver.addConstr(U[(taskLevel, costLevel, core.coreID)] - W[coreIDtoIndex[core.coreID]] * (x2 - x1)
                                                >= x1 - numWays * (x2 - x1) + I_A_term + schedCtxABterm)
                        else:
                            solver.addConstr(U[(taskLevel,costLevel,core.coreID)] - W[coreIDtoIndex[core.coreID]] * (x2 - x1)
                                                >= x1 - numWays * (x2 - x1))

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
            m = len(cluster.coresThisCluster)

            solver.addConstr(sum(U[(Constants.LEVEL_A, Constants.LEVEL_C, core.coreID)] + U[(
                                Constants.LEVEL_B, Constants.LEVEL_C, core.coreID)] for core in cluster.coresThisCluster) + U[(
                                    Constants.LEVEL_C, Constants.LEVEL_C, cluster.clusterID)] <= m)

            solver.addConstr( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                              for core in cluster.coresThisCluster) +
                              (m-1) * h[cluster.clusterID] +  H[cluster.clusterID]
                              <= m - EPSILON )

            #set objective function
        solver.setObjective( sum(U[(Constants.LEVEL_A,Constants.LEVEL_C,core.coreID)] + U[(Constants.LEVEL_B,Constants.LEVEL_C,core.coreID)]
                                    for core in complex.coreList) + sum(U[(Constants.LEVEL_C,Constants.LEVEL_C,cluster.clusterID)]
                                       for cluster in complex.clusterList), GRB.MINIMIZE)

        self.setParam(solver)

        solver.optimize()

        if solver.status == GRB.OPTIMAL:
            if Constants.DEBUG:
                print("---- complex ", complex.complexID, "-----")
            for core in complex.coreList:
                size = W[coreIDtoIndex[core.coreID]].x #size has num of ways
                core.cacheAB = [size, size] #[halfways, halfways]
                core.cacheC = W[-1].x * 2

                if Constants.DEBUG:
                    print(core.coreID, core.cacheAB, core.cacheC)
            if Constants.DEBUG:
                print("-----------")

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