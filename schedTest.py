from taskSystem import taskSystem
from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem
from constants import Constants
from overheads import Overheads


def schedTestTaskSystem(taskSystem, overhead, scheme, dedicatedIRQ, dedicatedIRQCore = None):
    '''
    sched test for full task system
    :param taskSystem: tasksystem to be tested
    :param overhead: overhead object with loaded data from
    :param scheme: considered cache allocation scheme
    :return:
    '''

    taskCount = len(taskSystem.levelA.tasksThisLevel) + len(taskSystem.levelB.tasksThisLevel) + len(taskSystem.levelC.tasksThisLevel)
    overhead.populateOverheadValue(taskCount=taskCount, allCriticalityLevels= taskSystem.levels) #populate inflation values that only depend on task count
    for coreComplex in taskSystem.platform.complexList:
        clusterIndex = 0
        for cluster in coreComplex.clusterList:
            U_A_C = U_B_C = U_C_C = 0
            if Constants.DEBUG:
                print()
                print("clusterID: ",cluster.clusterID, " num of levelC tasks: ", len(cluster.taskList))

            for core in cluster.coresThisCluster:
                if Constants.DEBUG:
                    print("coreID: ", core.coreID, " level A pairs: ", len(core.pairsOnCore[Constants.LEVEL_A]),
                        " level B pairs: ", len(core.pairsOnCore[Constants.LEVEL_B]))
                    print()
                levelAPairsOnCore = core.pairsOnCore[Constants.LEVEL_A]
                #set min level-A period
                if len(levelAPairsOnCore) > 0:
                    levelAAllTasks = taskSystem.levelA.tasksThisLevel
                    levelAStartingIndex = levelAAllTasks[0].ID
                    core.minLevelAPeriod = 999999999
                    for pair in levelAPairsOnCore:
                        core.minLevelAPeriod = min(core.minLevelAPeriod,levelAAllTasks[pair[0]-levelAStartingIndex].period)

                # level A tasks inflation accross all levels of exec
                levelAInflatedUtil = overhead.accountOverheadCore(taskLevel=Constants.LEVEL_A, allCritLevels=taskSystem.levels,
                                             core=core, cacheSize=core.getAssignedCache(Constants.LEVEL_A), scheme=scheme,
                                             dedicatedIRQ = dedicatedIRQ, dedicatedIRQCore = dedicatedIRQCore)

                #level B tasks inflation accross all at or below levels of exec
                levelBInflatedUtil = overhead.accountOverheadCore(taskLevel=Constants.LEVEL_B,
                                                                  allCritLevels=taskSystem.levels,
                                                                  core=core,
                                                                  cacheSize=core.getAssignedCache(Constants.LEVEL_B),scheme=scheme,
                                                                  dedicatedIRQ=dedicatedIRQ,
                                                                  dedicatedIRQCore=dedicatedIRQCore)

                #cache delay due to cache affinity loss by preemption of level-B tasks by level-A tasks
                cpmdLevelAB = overhead.CPMDInflationLevelAB(pairs=core.pairsOnCore[Constants.LEVEL_A],core=core,
                                                            allCriticalityLevels=taskSystem.levels,
                                                            cacheSize = core.getAssignedCache(Constants.LEVEL_B),
                                                            scheme = scheme,
                                                            dedicatedIRQ=dedicatedIRQ,dedicatedIRQCore=dedicatedIRQCore)

                #U_taskLevel_costLevel
                U_A_A_core = sum(levelAInflatedUtil[(pair,Constants.LEVEL_A)] for pair in core.pairsOnCore[Constants.LEVEL_A])
                U_A_B_core = sum(levelAInflatedUtil[(pair,Constants.LEVEL_B)] for pair in core.pairsOnCore[Constants.LEVEL_A]) + cpmdLevelAB[Constants.LEVEL_B]
                U_A_C_core = sum(levelAInflatedUtil[(pair,Constants.LEVEL_C)] for pair in core.pairsOnCore[Constants.LEVEL_A]) + cpmdLevelAB[Constants.LEVEL_C]

                #cond 1
                if U_A_A_core > 1:
                    return False

                U_B_B_core = sum(levelBInflatedUtil[(pair, Constants.LEVEL_B)] for pair in core.pairsOnCore[Constants.LEVEL_B])
                U_B_C_core = sum(levelBInflatedUtil[(pair, Constants.LEVEL_C)] for pair in core.pairsOnCore[Constants.LEVEL_B])

                #cond2
                if U_A_B_core + U_B_B_core > 1:
                    return False

                U_A_C += U_A_C_core
                U_B_C += U_B_C_core

            #at most one core complex can have two level-C clusters (one solo and one threaded)
            if len(coreComplex.clusterList)>1:
                levelCInflatedUtil = overhead.accountOverheadCluster(taskLevel=Constants.LEVEL_C,
                                                                     allCritLevels=taskSystem.levels,
                                                                     cluster=cluster,
                                                                     cacheSize=cluster.coresThisCluster[
                                                                         0].getAssignedCache(Constants.LEVEL_C),
                                                                     additionalCluster= coreComplex.clusterList[(clusterIndex+1)%2],
                                                                     dedicatedIRQ=dedicatedIRQ,
                                                                     dedicatedIRQCore=dedicatedIRQCore)
            else:
                levelCInflatedUtil = overhead.accountOverheadCluster(taskLevel=Constants.LEVEL_C, allCritLevels=taskSystem.levels,
                                                          cluster=cluster, cacheSize=cluster.coresThisCluster[0].getAssignedCache(Constants.LEVEL_C),
                                                          dedicatedIRQ = dedicatedIRQ, dedicatedIRQCore = dedicatedIRQCore)
            U_C_C += sum(levelCInflatedUtil[(task.ID, Constants.LEVEL_C)] for task in cluster.taskList)

            levelCUtilValues = list(levelCInflatedUtil.values())
            sortedLeveCInflatedUtil = sorted(levelCUtilValues,reverse=True)
            h = sortedLeveCInflatedUtil[0]
            H = 0
            m=len(cluster.coresThisCluster)
            for i in range(0,min(m-1,len(sortedLeveCInflatedUtil))):
                H += sortedLeveCInflatedUtil[i]

            #cond3,4
            if U_A_C + U_B_C + U_C_C > m:
                return False
            if U_A_C + U_B_C + (m-1) * h + H >= m:
                return False

    return True

