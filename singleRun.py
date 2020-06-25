from taskSystem import taskSystem
from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem
from constants import Constants
from overheads import Overheads
from schedTest import *
from LLCAllocation import LLCAllocation
import random

def main():
    totalCores = 6
    coresPerComplex = 2
    cacheSizeL3 = 2
    random.seed(12345)
    assumedCache = cacheSizeL3

    # Test levels A and B
    fileLevelA = "levelA-v1.csv"
    fileLevelB = "levelB-v1.csv"
    fileLevelC = "levelC-v1.csv"

    mySystem = taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    # test level A
    mySystem.levelA.loadSystem(fileLevelA)

    mySystem.levelA.setPairsList()
    success = mySystem.levelA.assignToCores(alg=Constants.WORST_FIT, coreList=mySystem.platform.coreList)
    if not success:
        print("failed to assign cores at level A")
        return
    # mySystem.printPairsByCore()

    # test level B
    mySystem.levelB.loadSystem(fileLevelB)
    mySystem.levelB.setPairsList()
    success = mySystem.levelB.assignToCores(alg=Constants.WORST_FIT, coreList=mySystem.platform.coreList)
    if not success:
        print("failed to assign cores at level A")
        return

    print("printing pairs by core: ")
    mySystem.printPairsByCore()

    # Test of level C
    fileLevelC = "levelC-v1.csv"
    mySystem.levelC.loadSystem(fileLevelC)
    mySystem.levelC.decideThreaded()
    # print solo tasks
    print("Solo tasks:")
    for t in mySystem.levelC.soloTasks:
        print(t.ID, t.currentSoloUtil)

    print()
    print("Threaded tasks:")
    for t in mySystem.levelC.threadedTasks:
        print(t.ID, t.currentThreadedUtil)

    mySystem.levelC.divideCores(mySystem.platform.coreList, coresPerComplex)

    mySystem.levelC.assignClusterID()
    mySystem.levelC.assignClustersToCoreComplex(mySystem.platform.complexList, coresPerComplex)

    print(len(mySystem.platform.complexList))
    for complex in mySystem.platform.complexList:
        print("complex: ", complex.complexID)
        for cluster in complex.clusterList:
            print(cluster.clusterID, len(cluster.coresThisCluster))
        print()

    print("Solo cores:")
    for c in mySystem.levelC.soloCores:
        print(c.coreID)
    print()
    print("Threaded cores:")
    for c in mySystem.levelC.threadedCores:
        print(c.coreID)

    mySystem.levelC.assignTasksToClusters()
    mySystem.printClusters()



    taskCount = 0
    for critLevels in mySystem.levels.values():
        taskCount += len(critLevels.tasksThisLevel)
    overhead = Overheads()
    overhead.loadOverheadData('oheads')
    taskCount = len(mySystem.levelA.tasksThisLevel) + len(mySystem.levelB.tasksThisLevel) + len(
        mySystem.levelC.tasksThisLevel)
    overhead.populateOverheadValue(taskCount=taskCount, allCriticalityLevels=mySystem.levels)
    solver = LLCAllocation()
    #mySystem.platform.complexList[1].clusterList = [] #check if can handle empty cluster
    #solver.threadWiseAllocation(mySystem, 8, overhead, mySystem.platform.complexList[1], coresPerComplex, True, mySystem.platform.coreList[0])
    print("\n")
    print("Basic Symmetric")
    for complex in mySystem.platform.complexList:
        if not solver.coreWiseAllocation(mySystem, 8, overhead, complex, coresPerComplex, True, mySystem.platform.coreList[0]):
            print("False")
            return

    print(schedTestTaskSystem(taskSystem=mySystem, overhead=overhead, dedicatedIRQ=True,
                                        dedicatedIRQCore=mySystem.platform.coreList[0]))

    overhead = Overheads()
    overhead.loadOverheadData('oheads')
    taskCount = len(mySystem.levelA.tasksThisLevel) + len(mySystem.levelB.tasksThisLevel) + len(
        mySystem.levelC.tasksThisLevel)
    overhead.populateOverheadValue(taskCount=taskCount, allCriticalityLevels=mySystem.levels)
    solver = LLCAllocation()
    print("\n")
    print("Assymmetric 2nd")
    for complex in mySystem.platform.complexList:
        if not solver.threadWiseAllocation2(mySystem, 8, overhead, complex, coresPerComplex, True, mySystem.platform.coreList[0]):
            print("False")
            return

    print(schedTestTaskSystem(taskSystem=mySystem, overhead=overhead, dedicatedIRQ=True,
                                        dedicatedIRQCore=mySystem.platform.coreList[0]))

    overhead = Overheads()
    overhead.loadOverheadData('oheads')
    taskCount = len(mySystem.levelA.tasksThisLevel) + len(mySystem.levelB.tasksThisLevel) + len(
        mySystem.levelC.tasksThisLevel)
    overhead.populateOverheadValue(taskCount=taskCount, allCriticalityLevels=mySystem.levels)
    solver = LLCAllocation()
    print("\n")
    print("Assymmetric 1st")
    for complex in mySystem.platform.complexList:
        if not solver.threadWiseAllocation(mySystem, 8, overhead, complex, coresPerComplex, True, mySystem.platform.coreList[0]):
            print("False")
            return

    print(schedTestTaskSystem(taskSystem=mySystem, overhead=overhead, dedicatedIRQ=True,
                                        dedicatedIRQCore=mySystem.platform.coreList[0]))


if __name__ == "__main__":
    main()