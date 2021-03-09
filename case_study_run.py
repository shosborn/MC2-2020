from taskSystem import taskSystem
from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem
from constants import Constants
from overheads import Overheads
from schedTest import *
from LLCAllocation import LLCAllocation
import os
from gurobipy import *
import csv
import time
import argparse

def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('-d', "--datafile", type = argparse.FileType('w'),
    # default = sys.stdout,
    # help = "File to output csv file to")
    parser.add_argument('-m', "--processors", default=Constants.NUM_CORES, type=int, help="Number of cores")
    parser.add_argument('-u', "--sysUtil", default=Constants.NUM_CORES, type=float, help="System utilization")
    parser.add_argument('-c', "--corePerComplex", default=Constants.CORES_PER_COMPLEX, type=int,
                        help="Number of cores per complex")
    #parser.add_argument('-p', "--period", default="All", help="Period distribution")
    #parser.add_argument('-s', "--smt", default="All", help="SMT effectiveness")
    #parser.add_argument('-u', "--util", default="All", help="per-task util")
    #parser.add_argument('-r', "--crit", default="All", help="criticality util")
    parser.add_argument('-l', "--limitThreadUtil", default=Constants.MAX_THREADED_UTIL, type=float,
                        help="Max threaded util")
    parser.add_argument('-A', "--levelA", default="TACLe", help="level-A benchmark")
    parser.add_argument('-B', "--levelB", default="TACLe", help="level-B benchmark")
    parser.add_argument('-C', "--levelC", default="SD-VBS", help="level-C benchmark")
    parser.add_argument('-f', "--filepath", help="file path")

    args = parser.parse_args()
    totalCores = args.processors
    # ugly, but easiest way to get numCores into titles
    #Constants.NUM_CORES = numCores
    coresPerComplex = args.corePerComplex
    #periodDist = args.period
    #smtDist = args.smt
    #critDist = args.crit
    #taskUtilDist = args.util
    # this is ugly and hacky, but having the limit as a scenario parameter causes its own problems.
    # downside is one command can only use one value for the util limit
    Constants.MAX_THREADED_UTIL = args.limitThreadUtil

    #totalCores = Constants.NUM_CORES
    #coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = Constants.CACHE_SIZE_L3

    assumedCache = cacheSizeL3
    targetUtil = args.sysUtil
    filePath = args.filepath
    dir =  os.path.split(filePath)[0]
    benchmark = {}
    benchmark[Constants.LEVEL_A] = args.levelA
    benchmark[Constants.LEVEL_B] = args.levelB
    benchmark[Constants.LEVEL_C] = args.levelC

    # Test levels A and B
    mySystem = taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    # test level A
    nextStartingID = mySystem.levelA.loadSystem(filePath, 0, targetUtil,benchmark[Constants.LEVEL_A])
    nextStartingID = mySystem.levelB.loadSystem(filePath, nextStartingID, targetUtil,benchmark[Constants.LEVEL_B])
    nextStartingID = mySystem.levelC.loadSystem(filePath, nextStartingID, targetUtil,benchmark[Constants.LEVEL_C])



    start = time.time()
    mySystem.levelA.setPairsList()
    success = mySystem.levelA.assignToCores(alg=Constants.WORST_FIT,
                                                   coreList=mySystem.platform.coreList, dedicatedIRQ=True)
    if not success:
        print("failed to assign cores at level A")
        return False
    # mySystem.printPairsByCore()
    #print("Level A core assigned")
    # test level B

    mySystem.levelB.setPairsList()
    success = mySystem.levelB.assignToCores(alg=Constants.WORST_FIT,
                                               coreList=mySystem.platform.coreList, dedicatedIRQ=True)
    if not success:
        print("failed to assign cores at level B")
        return False
    #print("Level B core assigned")
    #print("printing pairs by core: ")
    #mySystem.printPairsByCore()


    # Test of level C
    #fileLevelC = "levelC-v1.csv"

    mySystem.levelC.decideThreaded()

    thread_decision = time.time() - start
    start = time.time()
    success=mySystem.levelC.divideCores(mySystem.platform.coreList, coresPerComplex, dedicatedIRQ=True)
    if not success:
        print("failed to divide core in clusters")
    #print("core divided into clusters")
    mySystem.levelC.assignClusterID()
    mySystem.levelC.assignClustersToCoreComplex(mySystem.platform.complexList, coresPerComplex)

    success = mySystem.levelC.assignTasksToClusters()
    partition_time = time.time() -start
    if not success:
        print("failed to assign cores at level C")
        return False


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
            print("LP solver failed")
            return False
    fileName = dir + "/l3alloc" + ".csv"
    with open(fileName, "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['core', 'levelAB', 'levelAB', 'levelC'])
        for core in mySystem.platform.coreList:
            if core.coreID == 0:
                continue
            csvwriter.writerow([core.coreID, core.cacheAB[0], core.cacheAB[1], core.cacheC / 2])

    with open(dir +'/levelAB_pairs'+ '.csv', "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(
            ['core','crit_level','task1 id','task1 name','task1 period', 'task2 id', 'task2 name', 'task2 period'])
        #for level in range(Constants.LEVEL_A, Constants.LEVEL_B + 1):
        coreList = mySystem.platform.coreList
        for c in coreList:
            for thisLevel in range(Constants.LEVEL_A, Constants.LEVEL_C):
                startingTaskID = mySystem.levels[thisLevel].tasksThisLevel[0].ID

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
    with open(dir + '/levelC_threads' + '.csv', "w", newline='\n', encoding='utf-8') as f:
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
    main()