# -*- coding: utf-8 -*-
"""
Created on Fri May  1 14:25:48 2020

@author: simsh
"""



from hardware_platform import HardwarePlatform
from crit_level import CritLevelSystem
from constants import Constants
from overheads import Overheads
from schedTest import *

class taskSystem:
    
    def __init__(self, totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA, fileLevelB, fileLevelC):

        self.platform=HardwarePlatform(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
        self.levelA=CritLevelSystem(Constants.LEVEL_A, assumedCache)
        self.levelB=CritLevelSystem(Constants.LEVEL_B, assumedCache)
        self.levelC=CritLevelSystem(Constants.LEVEL_C, assumedCache)

        self.levels = []
        self.levels.extend([self.levelA,self.levelB,self.levelC])
        
        print("Initial list of levels:")
        print(self.levels)

    def printPairsByCore(self):
        coreList=self.platform.coreList
        for c in coreList:
            print(c.coreID)
            
            for thisLevel in range(Constants.LEVEL_A, Constants.LEVEL_C):
                #print(self.levels[thisLevel].tasksThisLevel)
                print("thisLevel=", thisLevel)
                #print(self.levels)
                print("Getting startingTaskID")
                # tasksThisLevel either doesn't exist or is empty if level hasn't been loaded
                
                startingTaskID=self.levels[thisLevel].tasksThisLevel[0].ID
                print("startingTaskID=", startingTaskID)
                if thisLevel==Constants.LEVEL_A:
                    print("Level A")
                else:
                    print("Level B")
                for p in c.pairsOnCore[thisLevel]:
                    # task1 and task2 are task IDs
                    task1=p[0]
                    task2=p[1]
                    period=self.levels[thisLevel].tasksThisLevel[task1-startingTaskID].period
                    util=self.levels[thisLevel].tasksThisLevel[task1-startingTaskID].allUtil[(task2, thisLevel, c.assignedCache)]
                    cost=util * period
                    print(task1, task2)
                    print("This level: ", cost, period, util)
                    for lowerLevel in range (thisLevel+1, Constants.LEVEL_C+1):
                        lowerUtil=self.levels[thisLevel].tasksThisLevel[task1-startingTaskID].allUtil[(task2, lowerLevel, c.assignedCache)]
                        print("Next level down: ", lowerUtil)
            print()


     # applies to Level C
    def printClusters(self):

        for thisCluster in self.levelC.soloClusters:
            print("Solo clusters:")
            # print list of cores in cluster
            print("Cores: ", end="")
            for core in thisCluster.coresThisCluster:
                print(core.coreID, end=" ")
            print()
            # print higher-level usage
            print("Higher level usage: ",  thisCluster.usedCapacityHigherLevels, sep=" ")
            # print list showing (taskID, util)
            for t in thisCluster.taskList:
                print("ID ",  t.ID, ", Util ", t.currentSoloUtil)
            print()

        for thisCluster in self.levelC.threadedClusters:
            print("Threaded clusters:")
            print("Cores: ", end="")
            for core in thisCluster.coresThisCluster:
                print(core.coreID, end=" ")
            print()
            print("Higher level usage: ", thisCluster.usedCapacityHigherLevels, sep=" ")
            for t in thisCluster.taskList:
                print("ID ", t.ID, ", Util ", t.currentThreadedUtil)
            print()


                
        

def main():
    totalCores=6
    coresPerComplex=2
    cacheSizeL3=2

    assumedCache=cacheSizeL3

    '''
    fileLevelA="levelA-v1.csv"
    #tasksFromFile=True

    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA)
    mySystem.levelA.loadSystem(fileLevelA)
    #mySystem.levelA=CritLevelSystem(Constants.LEVEL_A, fileLevelA, assumedCache)
    mySystem.levelA.setPairsList()
    #pairsByCore=mySystem.levelA.assignToClusters(WORST_FIT)
    mySystem.levelA.assignToCores(Constants.WORST_FIT, mySystem.platform.coreList)
    #mySystem.printPairsByCore()
    '''
    
    #Test levels A and B
    fileLevelA="levelA-v1.csv"
    fileLevelB="levelB-v1.csv"
    fileLevelC="levelC-v1.csv"
    
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache,
                        fileLevelA, fileLevelB, fileLevelC)
    # test level A
    mySystem.levelA.loadSystem(fileLevelA)

    mySystem.levelA.setPairsList()
    success = mySystem.levelA.assignToCores(alg=Constants.WORST_FIT, coreList=mySystem.platform.coreList)
    if not success:
        print("failed to assign cores at level A")
        return
    #mySystem.printPairsByCore()
    
    # test level B
    mySystem.levelB.loadSystem(fileLevelB)
    mySystem.levelB.setPairsList()
    success = mySystem.levelB.assignToCores(alg=Constants.WORST_FIT, coreList=mySystem.platform.coreList)
    if not success:
        print("failed to assign cores at level A")
        return
   
    
    mySystem.printPairsByCore()

    # Test of level C
    fileLevelC="levelC-v1.csv"
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
    mySystem.levelC.assingClustersToCoreComplex(mySystem.platform.complexList, coresPerComplex)

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
    for critLevels in mySystem.levels:
        taskCount += len(critLevels.tasksThisLevel)
    overhead = Overheads()
    overhead.loadOverheadData('oheads')

    print(schedTestTaskSystem(taskSystem=mySystem, overhead=overhead, scheme=Constants.THREAD_LEVEL_ISOLATION,
                              dedicatedIRQ=True, dedicatedIRQCore=mySystem.platform.coreList[0]))
    print(schedTestTaskSystem(taskSystem=mySystem, overhead=overhead, scheme=Constants.CORE_LEVEL_ISOLATION,
                              dedicatedIRQ=True, dedicatedIRQCore=mySystem.platform.coreList[0]))




if __name__== "__main__":
     main()