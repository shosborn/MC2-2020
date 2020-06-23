from constants import Constants
from taskSystem import taskSystem
import distributions
import numpy as np
from numpy import random
import itertools
import argparse
import scipy.stats
import math
from typing import Dict, Tuple

def generateScenario():
    #goal: return a scenario corresponding to every possible combination

    paramList = {'critUtilDist':Constants.CRITICALITY_UTIL_DIST.keys(), 
                 'periodDist':Constants.PERIOD_DIST.keys(), 
                 'taskUtilDist':Constants.TASK_UTIL.keys(),
                 'possCacheSensitivity':Constants.CACHE_SENSITIVITY.keys(),
                 'wssDist':Constants.WSS_DIST.keys(),
                 'smtEffectDist':Constants.SMT_EFFECTIVENESS_DIST.keys(),
                 'critSensitivity':Constants.CRIT_SENSITIVITY.keys()
                 }

    
    keys = paramList.keys()
    
    vals = paramList.values()
    for instance in itertools.product(*vals):
        yield dict(zip(keys, instance))



def _get_util_caps_per_crit(scenario: Dict[str, str]) -> Dict[int,float]:
    util_dist_per_crit = Constants.CRITICALITY_UTIL_DIST[scenario['critUtilDist']]
    util_caps_per_crit = {}
    for key in util_dist_per_crit.keys():
        util_caps_per_crit[key] = distributions.sample_unif_distribution(util_dist_per_crit[key])
    total_caps = sum([util_caps_per_crit[key] for key in util_caps_per_crit.keys()])
    for key in util_caps_per_crit.keys():
        util_caps_per_crit[key] /= total_caps
    return util_caps_per_crit

def generateTaskSystem(scenario, sysUtil):
    # for now loading task system from sample file
    totalCores = Constants.NUM_CORES
    coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = 2

    assumedCache = cacheSizeL3
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)

    
    # generate tasks for all levels
    cTargetUtilByLevel=[]
    for thisLevel in mySystem.levels:
        i=thisLevel.level
        if i==Constants.LEVEL_A:
            startingID=1
        else:
            startingID=len(mySystem.levels[i-1].tasksThisLevel)+1
        
        if i == Constants.LEVEL_A or i == Constants.LEVEL_B:
            lb=Constants.CRITICALITY_UTIL_DIST[scenario['critUtilDist']][i][0]
            ub=Constants.CRITICALITY_UTIL_DIST[scenario['critUtilDist']][i][1]
            # multiply random value by (difference between level and C + 1) to get target util
            cTargetUtil=random.uniform(lb, ub) * sysUtil
            cTargetUtilByLevel.append(cTargetUtil)
            targetUtil=cTargetUtil / (Constants.CRIT_SENSITIVITY * (Constants.LEVEL_C - i + 1))
            
        else:
            # targetUtil for level C; however much of sysUtil is leftover
            targetUtil = sysUtil - sum(cTargetUtilByLevel)
        
        thisLevel.createTasks(
                Constants.PERIOD_DIST[scenario['periodDist']][i],
                targetUtil,
                Constants.TASK_UTIL[scenario['taskUtilDist']][i],
                Constants.CACHE_SENSITIVITY[scenario['possCacheSensitivity']],
                Constants.SMT_EFFECTIVENESS_DIST[scenario['smtEffectDist']][i],
                Constants.WSS_DIST[scenario['wssDist']],
                Constants.CRIT_SENSITIVITY,
                startingID
                )

    return mySystem

def compute_z_value():
    assert(0 <= Constants.CONF_LEVEL < 1)
    return scipy.stats.norm.ppf(1 - (1 - Constants.CONF_LEVEL)/2)

def normal_approx_error(mean: float, samples: int):
    """
    Determine if sufficient samples have been collected for statistical significance
    :param mean:
    :param samples:
    :return: True if iterations should continue, otherwise False
    """
    assert(0 <= mean <= 1)
    assert(samples >= 0)
    assert(Constants.CONF_INTERVAL > 0)

    if samples == 0:
        return True

    z = compute_z_value()
    err = z*math.sqrt(mean*(1-mean)/samples)

    return err > Constants.CONF_INTERVAL


def schedStudySingleScenario(scenario,numCores,corePerComplex):
    # if running this takes too long, set startUtil to numCores/2
    startUtil = numCores / 2
    endUtil = 2 * numCores

    for sysUtil in np.arange(startUtil, endUtil + Constants.UTIL_STEP_SIZE, Constants.UTIL_STEP_SIZE):
        # assuming task sets are generated on the fly, otherwise read from csv file by loadSystem if pre-generated
        # assuming a TaskSystem object is returned
        numSamples = 0
        sched_ratio = 0
        #need to change it with some statistical significance test?
        while Constants.MIN_SAMPLES < numSamples < Constants.MAX_SAMPLES\
                and normal_approx_error(sched_ratio, numSamples):
            #taskSystem = generateTaskSystem(scenario['utilDist'], scenario['period'], scenario['taskUtil'], sysUtil)
            taskSystem = generateTaskSystem(scenario, sysUtil)

            #sched1: MC2-SMT-with-isolation
            # taskSystem.levelA.loadSystem(fileLevelA)
            taskSystem.levelA.setPairsList()
            taskSystem.levelA.assignToCores(alg=Constants.WORST_FIT, coreList=taskSystem.platform.coreList)
            #print(taskSystem.levelA.schedulabilityTest(coreList=taskSystem.platform.coreList,
            #                                           allCritLevels=taskSystem.levels))
            # mySystem.printPairsByCore()

            # test level B
            # taskSystem.levelB.loadSystem(fileLevelB)
            taskSystem.levelB.setPairsList()
            taskSystem.levelB.assignToCores(alg=Constants.WORST_FIT, coreList=taskSystem.platform.coreList)
            #print(taskSystem.levelB.schedulabilityTest(coreList=taskSystem.platform.coreList,
            #                                           allCritLevels=taskSystem.levels))

            #taskSystem.printPairsByCore()

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
            #print(taskSystem.levelC.schedulabilityTest(coreList=taskSystem.platform.coreList,
            #                                           allCritLevels=taskSystem.levels))

            #todo: other schedulers to compare

            #todo: update counters, mean, std dev, etc.
            numSamples += 1

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
        #print(scenario)
        schedStudySingleScenario(scenario,numCores,corePerComplex)

    return

if __name__ == '__main__':
    main()