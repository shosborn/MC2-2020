from taskSystem import taskSystem
from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem
from constants import Constants
from overheads import Overheads
from schedTest import *
from LLCAllocation import LLCAllocation
import random
from gurobipy import *
import csv
import os
import time

def main(targetUtil, benchmark, iter=None):
    totalCores = Constants.NUM_CORES
    coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = Constants.CACHE_SIZE_L3
    outdir = "case_study_tasks"
    if iter is not None:
        outdir = "case_study_tasks/"+str(iter)

    assumedCache = cacheSizeL3
    targetUtil = targetUtil

    # Test levels A and B
    file = "temp_task_set.csv"
    #fileLevelB = "case study\\dis-abmod-light-10(2).csv"
    #fileLevelC = "case study\\dis-abmod-light-10(2).csv"
    #benchmark = {Constants.LEVEL_A: 'TACLe', Constants.LEVEL_B: 'TACLe', Constants.LEVEL_C: 'DIS'}
    mySystem = taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    # test level A
    nextStartingID = mySystem.levelA.loadSystem(file, 0, targetUtil,benchmark[Constants.LEVEL_A])
    nextStartingID = mySystem.levelB.loadSystem(file, nextStartingID, targetUtil,benchmark[Constants.LEVEL_B])
    nextStartingID = mySystem.levelC.loadSystem(file, nextStartingID, targetUtil,benchmark[Constants.LEVEL_C])


    start = time.time()
    mySystem.levelA.setPairsList()
    success = mySystem.levelA.assignToCores(alg=Constants.WORST_FIT,
                                                   coreList=mySystem.platform.coreList, dedicatedIRQ=True)
    if not success:
        #print("failed to assign cores at level A")
        return False
    # mySystem.printPairsByCore()
    #print("Level A core assigned")
    # test level B

    mySystem.levelB.setPairsList()
    success = mySystem.levelB.assignToCores(alg=Constants.WORST_FIT,
                                               coreList=mySystem.platform.coreList, dedicatedIRQ=True)
    if not success:
        #print("failed to assign cores at level B")
        return False

    mySystem.levelC.decideThreaded()

    thread_decision = time.time() - start
    start = time.time()
    success=mySystem.levelC.divideCores(mySystem.platform.coreList, coresPerComplex, dedicatedIRQ=True)
    if not success:
        #print("failed to divide core in clusters")
        return False
    #print("core divided into clusters")
    mySystem.levelC.assignClusterID()
    mySystem.levelC.assignClustersToCoreComplex(mySystem.platform.complexList, coresPerComplex)

    success = mySystem.levelC.assignTasksToClusters()
    partition_time = time.time() -start
    if not success:
        #print("failed to assign cores at level C")
        return False
    #print("core assigned at level C")
    #mySystem.printClusters()


    overhead = Overheads()
    overhead.loadOverheadData('oheads')
    start = time.time()
    taskCount = len(mySystem.levelA.tasksThisLevel) + len(mySystem.levelB.tasksThisLevel) + len(
        mySystem.levelC.tasksThisLevel)
    overhead.populateOverheadValue(taskCount=taskCount, allCriticalityLevels=mySystem.levels)

    solver = LLCAllocation()
    #mySystem.platform.complexList[1].clusterList = [] #check if can handle empty cluster
    #solver.threadWiseAllocation(mySystem, 8, overhead, mySystem.platform.complexList[1], coresPerComplex, True, mySystem.platform.coreList[0])

    for curr_complex in mySystem.platform.complexList:
        #print("complex: ", curr_complex)
        success = solver.coreWiseAllocation(mySystem, totalCores, overhead, curr_complex, len(curr_complex.coreList),
                                  True,
                                  mySystem.platform.coreList[0])
        if success is not GRB.OPTIMAL:
        #    print("LP solver failed")
            return False
    if not os.path.isdir(outdir):
        os.mkdir(outdir)

    fileName = outdir+"/l3alloc.csv"
    with open(fileName, "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['core', 'levelAB', 'levelAB', 'levelC'])
        for core in mySystem.platform.coreList:
            if core.coreID == 0:
                continue
            csvwriter.writerow([core.coreID, core.cacheAB[0], core.cacheAB[1], core.cacheC / 2])

    cache_decison = time.time() - start
    #print("--- times ---")
    print(thread_decision,partition_time,cache_decison)
    with open(outdir+'/all_tasks.csv', "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['task id','suite','benchmark','crit level','level-A pet(us)','period (ms)','wss'])
        for level in range(Constants.LEVEL_A, Constants.LEVEL_C+1):
            for task in mySystem.levels[level].tasksThisLevel:
                csvwriter.writerow(
                    [task.ID, benchmark[level], task.name, task.level, task.baseCost, task.period/1000, task.wss])

    with open(outdir+'/levelAB_pairs.csv', "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(
            ['core','crit_level','task1 id','task1 name','task1 period', 'task2 id', 'task2 name', 'task2 period'])
        #for level in range(Constants.LEVEL_A, Constants.LEVEL_B + 1):
        coreList = mySystem.platform.coreList
        for c in coreList:
            for thisLevel in range(Constants.LEVEL_A, Constants.LEVEL_C):
                startingTaskID = mySystem.levels[thisLevel].tasksThisLevel[0].ID
                '''if thisLevel == Constants.LEVEL_A:
                    print("Level A")
                else:
                    print("Level B")'''
                for p in c.pairsOnCore[thisLevel]:
                    task1 = p[0]
                    task2 = p[1]
                    #print(task1, task2)
                    t1 = mySystem.levels[thisLevel].tasksThisLevel[task1 - startingTaskID]
                    t2 = mySystem.levels[thisLevel].tasksThisLevel[task2 - startingTaskID]
                    csvwriter.writerow(
                        [c.coreID,thisLevel,t1.ID,t1.name,t1.period/1000,t2.ID,t2.name,t2.period/1000])
                        #print(t1.ID, ",", t1.name, ",", t1.period / 1000)
                        #print(t2.ID, ",", t2.name, ",", t2.period / 1000)
                        # print("This level: ", cost, period, util)
            #print()
    with open(outdir+'/levelC_threads.csv', "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        for thisCluster in mySystem.levelC.soloClusters:
            solo_cores = ['solo']
            for core in thisCluster.coresThisCluster:
                solo_cores.append(core.coreID)
            #solo_cores = solo_cores + list(thisCluster.coresThisCluster)
            csvwriter.writerow(solo_cores)
            csvwriter.writerow([])
            csvwriter.writerow(['task id','name','period'])
            for t in thisCluster.taskList:
                csvwriter.writerow([t.ID,t.name,t.period / 1000])

        for thisCluster in mySystem.levelC.threadedClusters:
            threaded_cores = ['threaded']
            for core in thisCluster.coresThisCluster:
                threaded_cores.append(core.coreID)
            csvwriter.writerow(threaded_cores)
            csvwriter.writerow([])
            csvwriter.writerow(['task id','name','period'])
            for t in thisCluster.taskList:
                csvwriter.writerow([t.ID, t.name, t.period / 1000])
    return True
if __name__ == "__main__":
    main(8)