from constants import Constants
from taskSystem import taskSystem
import numpy as np
import itertools
import argparse

def generateScenario():
    paramList = {'utilDist':Constants.CRITICALITY_UTIL_DIST.keys(), 'period':Constants.PERIOD_DIST.keys(), 'taskUtil':Constants.TASK_UTIL.keys()}
    keys = paramList.keys()
    vals = paramList.values()
    for instance in itertools.product(*vals):
        yield dict(zip(keys, instance))

def generateTaskSystem(utilDist,period,taskUtil,sysUtil):
    # for now loading task system from sample file
    totalCores = Constants.NUM_CORES
    coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = 2

    assumedCache = cacheSizeL3
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    
    '''
    To define for each level:
        tuple possiblePeriods
            for levels A and B, will choose one value from tuple at random
            for level C, choose one value from a uniform distribution
        float targetUtil
            maximum total utilization of solo util given cacheSizeL3
        tuple taskUtilDis
        CacheSensitivity
            choose one value from tuple at random for each task
        tuple smtEffectDis
            gives distribution parameters
        seed: random seed
        wss: set of wss values to consider

    '''
    
    for thisLevel in mySystem.levels:
        
        i=thisLevel.level
        if i==Constants.LEVEL_A:
            startingID=1
        else:
            startingID=len(mySystem.levels[i-1].tasksThisLevel)+1
        
        thisLevel.createTasks(possiblePeriods[i], targetUtil[i], taskUtilDis[i], possibleCacheSensitivity[i], smtEffectDis[i], possibleWSS[i], startingID)

    
    '''
    # old version that used pre-defined tasks
    fileLevelA = "levelA-v1.csv"
    fileLevelB = "levelB-v1.csv"
    fileLevelC = "levelC-v1.csv"
    
    mySystem = taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache,
                          fileLevelA, fileLevelB, fileLevelC)
    mySystem.levelA.loadSystem(fileLevelA)
    mySystem.levelB.loadSystem(fileLevelB)
    mySystem.levelC.loadSystem(fileLevelC)
    '''

    return mySystem

def schedStudySingleScenario(scenario,numCores,corePerComplex):
    startUtil = 0
    endUtil = 2 * numCores

    for sysUtil in np.arange(startUtil, endUtil + Constants.UTIL_STEP_SIZE, Constants.UTIL_STEP_SIZE):
        # assuming task sets are generated on the fly, otherwise read from csv file by loadSystem if pre-generated
        # assuming a TaskSystem object is returned
        numSamples = 0

        #need to change it with some statsitical significance test?
        while numSamples < Constants.MAX_SAMPLES:
            taskSystem = generateTaskSystem(scenario['utilDist'], scenario['period'], scenario['taskUtil'], sysUtil)

            #sched1: MC2-SMT-with-isolation
            # taskSystem.levelA.loadSystem(fileLevelA)
            taskSystem.levelA.setPairsList()
            taskSystem.levelA.assignToCores(alg=Constants.WORST_FIT, coreList=taskSystem.platform.coreList)
            print(taskSystem.levelA.schedulabilityTest(coreList=taskSystem.platform.coreList,
                                                       allCritLevels=taskSystem.levels))
            # mySystem.printPairsByCore()

            # test level B
            # taskSystem.levelB.loadSystem(fileLevelB)
            taskSystem.levelB.setPairsList()
            taskSystem.levelB.assignToCores(alg=Constants.WORST_FIT, coreList=taskSystem.platform.coreList)
            print(taskSystem.levelB.schedulabilityTest(coreList=taskSystem.platform.coreList,
                                                       allCritLevels=taskSystem.levels))

            taskSystem.printPairsByCore()

            # Test of level C
            # taskSystem.levelC.loadSystem(fileLevelC)
            taskSystem.levelC.decideThreaded()
            # print solo tasks
            '''print("Solo tasks:")
            for t in taskSystem.levelC.soloTasks:
                print(t.ID, t.currentSoloUtil)'''

            '''print()
            print("Threaded tasks:")
            for t in taskSystem.levelC.threadedTasks:
                print(t.ID, t.currentThreadedUtil)'''

            taskSystem.levelC.divideCores(taskSystem.platform.coreList, corePerComplex)
            '''print("Solo cores:")
            for c in taskSystem.levelC.soloCores:
                print(c.coreID)
            print()
            print("Threaded cores:")
            for c in taskSystem.levelC.threadedCores:
                print(c.coreID)'''

            taskSystem.levelC.assignTasksToClusters()
            taskSystem.printClusters()
            print(taskSystem.levelC.schedulabilityTest(coreList=taskSystem.platform.coreList,
                                                       allCritLevels=taskSystem.levels))

            #todo: other schedulers to compare

            #todo: update counters, mean, std dev, etc.

        #todo: for this sysUtil write sched ratios to file

    return


def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('-d', "--datafile", type = argparse.FileType('w'),
    # default = sys.stdout,
    # help = "File to output csv file to")
    parser.add_argument('-m', "--processors", default=Constants.NUM_CORES, type=int, help="Number of cores")
    parser.add_argument('-c', "--corePerComplex", default=Constants.CORES_PER_COMPLEX, type=int, help="Number of cores per complex")
    args = parser.parse_args()
    numCores = args.processors
    corePerComplex = args.corePerComplex

    scenarios = generateScenario()

    # to-do: parallel execution of scenarios?
    for scenario in scenarios:
        print(scenario)
        schedStudySingleScenario(scenario,numCores,corePerComplex)

    return

if __name__ == '__main__':
    main()