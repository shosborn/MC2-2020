from constants import Constants
from taskSystem import taskSystem

import distributions
import run_info

import numpy as np
from numpy import random
import itertools
import argparse
import scipy.stats
import math
from typing import Dict, Tuple
import time

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
    """
    Get what fraction of the system utilization is represented at each level
    :param scenario:
    :return: Dict[crit_level, fraction in [0,1]]
    """
    util_dist_per_crit = Constants.CRITICALITY_UTIL_DIST[scenario['critUtilDist']]
    util_caps_per_crit = {}
    for key in util_dist_per_crit.keys():
        util_caps_per_crit[key] = distributions.sample_unif_distribution(util_dist_per_crit[key])
    total_caps = sum([util_caps_per_crit[key] for key in util_caps_per_crit.keys()])
    for key in util_caps_per_crit.keys():
        util_caps_per_crit[key] /= total_caps
    return util_caps_per_crit

def generateTaskSystem(scenario, sysUtil, r_info):
    # for now loading task system from sample file
    totalCores = Constants.NUM_CORES
    coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = 2

    assumedCache = cacheSizeL3
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)

    util_caps_per_crit = _get_util_caps_per_crit(scenario)
    # generate tasks for all levels
    # We're assuming sysUtil refers to total Level-C utilization
    startingID = 1
    for level in range(Constants.MAX_LEVEL):
        targetUtil = sysUtil*util_caps_per_crit[level]
        critLevel = mySystem.levels[level]
        if r_info.timekeeping:
            generate_start = time.clock()
        newTasks = critLevel.createTasks(scenario, targetUtil, startingID)
        if r_info.verbose:
            print('Generated %d tasks in level %d' % (newTasks, level))
        startingID += newTasks
        if r_info.timekeeping:
            print('Time to generate crit level was %d seconds' % int(time.clock() - generate_start))

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


def schedStudySingleScenario(scenario,numCores,corePerComplex,r_info):
    # if running this takes too long, set startUtil to numCores/2
    startUtil = numCores / 2
    endUtil = 2 * numCores

    for sysUtil in np.arange(startUtil, endUtil + Constants.UTIL_STEP_SIZE, Constants.UTIL_STEP_SIZE):
        # assuming task sets are generated on the fly, otherwise read from csv file by loadSystem if pre-generated
        # assuming a TaskSystem object is returned
        numSamples = 0
        sched_ratio = 0
        #need to change it with some statistical significance test?
        while numSamples < Constants.MIN_SAMPLES or normal_approx_error(sched_ratio, numSamples):
            if numSamples > Constants.MAX_SAMPLES:
                break
            if r_info.timekeeping:
                generate_start = time.clock()
            taskSystem = generateTaskSystem(scenario, sysUtil, r_info)
            if r_info.timekeeping:
                print('Time to generate task system was %d seconds' % int(time.clock() - generate_start))

            taskSystem.levelA.setPairsList()
            taskSystem.levelA.assignToCores(alg=Constants.WORST_FIT, coreList=taskSystem.platform.coreList)

            taskSystem.levelB.setPairsList()
            taskSystem.levelB.assignToCores(alg=Constants.WORST_FIT, coreList=taskSystem.platform.coreList)

            taskSystem.levelC.decideThreaded()
            taskSystem.levelC.divideCores(taskSystem.platform.coreList, corePerComplex)

            taskSystem.levelC.assignTasksToClusters()
            taskSystem.printClusters()

            #todo: other schedulers to compare

            #todo: update counters, mean, std dev, etc.
            numSamples += 1
            sched_ratio = sched_ratio*(numSamples-1)/numSamples + 0.5/numSamples

        #todo: for this sysUtil write sched ratios to file
        if r_info.verbose:
            print('numSamples = %d' % numSamples)

    return


def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('-d', "--datafile", type = argparse.FileType('w'),
    # default = sys.stdout,
    # help = "File to output csv file to")
    parser.add_argument('-m', "--processors", default=Constants.NUM_CORES, type=int, help="Number of cores")
    parser.add_argument('-c', "--corePerComplex", default=Constants.CORES_PER_COMPLEX, type=int, help="Number of cores per complex")
    parser.add_argument('-t', "--timekeeping", action='store_true', help="Track time spent")
    parser.add_argument('-v', "--verbose", action='store_true', help="Output print statements")
    args = parser.parse_args()
    numCores = args.processors
    corePerComplex = args.corePerComplex
    r_info = run_info.RunInfo(args.timekeeping, args.verbose)

    scenarios = generateScenario()

    # to-do: parallel execution of scenarios?
    for scenario in scenarios:
        #print(scenario)
        if r_info.timekeeping:
            scenario_start = time.clock()
        schedStudySingleScenario(scenario,numCores,corePerComplex, r_info)
        if r_info.timekeeping:
            print('Scenario took %d seconds' % time.clock() - scenario_start)

    return

if __name__ == '__main__':
    main()