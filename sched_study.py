from constants import Constants
from taskSystem import taskSystem
from LLCAllocation import LLCAllocation
from overheads import Overheads

import distributions
from gurobipy import *

import numpy as np
#from numpy import random
import itertools
import argparse
import scipy.stats
import math
from typing import Dict, List, Tuple
import time


from csv import DictWriter

import multiprocessing

def title(scenario: Dict[str,str]) -> str:
    return '__'.join([scenario['critUtilDist'],
                      scenario['periodDist'],
                      scenario['taskUtilDist'],
                      scenario['possCacheSensitivity'],
                      scenario['wssDist'],
                      scenario['smtEffectDist'],
                      scenario['critSensitivity']
    ])

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
    total_caps = sum(util_caps_per_crit.values())
    for key in util_caps_per_crit.keys():
        util_caps_per_crit[key] /= total_caps
    return util_caps_per_crit

def generateTaskSystem(scenario, sysUtil):
    # for now loading task system from sample file
    totalCores = Constants.NUM_CORES
    coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = Constants.CACHE_SIZE_L3

    assumedCache = cacheSizeL3
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)

    util_caps_per_crit = _get_util_caps_per_crit(scenario)
    # generate tasks for all levels
    # We're assuming sysUtil refers to total Level-C utilization
    startingID = 1
    for level in range(Constants.MAX_LEVEL):
        targetUtil = sysUtil*util_caps_per_crit[level]
        critLevel = mySystem.levels[level]
        if Constants.TIMEKEEPING:
            generate_start = time.clock()
        newTasks = critLevel.createTasks(scenario, targetUtil, startingID)
        if Constants.VERBOSE:
            print('COUNT,Crit_Level,%d,%d' % (newTasks, level))
        startingID += newTasks
        if Constants.TIMEKEEPING:
            print('TIME,Crit_Level,%d' % int(time.clock() - generate_start))

    return mySystem

def cloneTaskSystem(oldSystem: taskSystem) -> taskSystem:
    totalCores = Constants.NUM_CORES
    coresPerComplex = Constants.CORES_PER_COMPLEX
    cacheSizeL3 = Constants.CACHE_SIZE_L3

    assumedCache = cacheSizeL3
    mySystem = taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache)
    for level in range(Constants.MAX_LEVEL):
        mySystem.levels[level].tasksThisLevel = oldSystem.levels[level].tasksThisLevel

    return mySystem

def compute_z_value():
    assert(0 <= Constants.CONF_LEVEL < 1)
    return scipy.stats.norm.ppf(1 - (1 - Constants.CONF_LEVEL)/2)

def normal_approx_error(mean_dict: Dict[int,float], samples: int):
    """
    Determine if sufficient samples have been collected for statistical significance
    :param mean_dict:
    :param samples:
    :return: True if iterations should continue, otherwise False
    """
    assert(samples >= 0)
    assert(Constants.CONF_INTERVAL > 0)
    if samples == 0:
        return True
    z = compute_z_value()
    for mean in mean_dict.values():
        assert(0 <= mean <= 1)
        err = z*math.sqrt(mean*(1-mean)/samples)
        if err > Constants.CONF_INTERVAL:
            return True

    return False

def seq_dps(dp: List[Tuple[Dict[str,str], float, int, int]], outfiles: Dict[str,DictWriter]) -> None:
    total_dp = len(dp)
    completed_dp = 0
    completed_dp_percent = 0
    for designpoint in dp:
        scenario, sysutil, sched_res_dict, \
            num_tasks_avg, time_avg, time_tot, \
            num_samples, debug_dict = schedStudySingleScenarioUtilUnpack(designpoint)
        rowDict = {'SYS_UTIL': sysutil,
                   'NO_THREAD': sched_res_dict[Constants.NO_THREAD],
                   'THREAD_COURSE': sched_res_dict[Constants.THREAD_COURSE],
                   'THREAD_FINE': sched_res_dict[Constants.THREAD_FINE],
                   'NUM_TASKS_AVG': num_tasks_avg,
                   'TIME_AVG': time_avg,
                   'TIME_TOTAL': time_tot,
                   'NUM_SAMPLES': num_samples
                   }
        if sum(sched_res_dict.values()) == 0.0:
            failureDict[title(scenario)][sysutil] = True
        for key in debug_dict.keys():
            rowDict[key] = debug_dict[key]
        outfiles[title(scenario)].writerow(rowDict)
        completed_dp += 1
        if int(100 * completed_dp / total_dp) > completed_dp_percent:
            completed_dp_percent = int(100 * completed_dp / total_dp)
            print('Completed %d%%' % completed_dp_percent)

def thread_dps(dp: List[Tuple[Dict[str,str], float, int, int]], outfiles: Dict[str,DictWriter]) -> None:
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    total_dp = len(dp)
    completed_dp = 0
    completed_dp_percent = 0
    try:
        for scenario, sysutil, sched_res_dict, \
            num_tasks_avg, time_avg, time_tot, \
                num_samples, debug_dict in pool.imap_unordered(schedStudySingleScenarioUtilUnpack, dp):
            rowDict = {'SYS_UTIL': sysutil,
                       'NO_THREAD': sched_res_dict[Constants.NO_THREAD],
                       'THREAD_COURSE': sched_res_dict[Constants.THREAD_COURSE],
                       'THREAD_FINE': sched_res_dict[Constants.THREAD_FINE],
                       'NUM_TASKS_AVG': num_tasks_avg,
                       'TIME_AVG': time_avg,
                       'TIME_TOTAL': time_tot,
                       'NUM_SAMPLES': num_samples
                       }
            if sum(sched_res_dict.values()) == 0.0:
                failureDict[title(scenario)][sysutil] = True
            for key in debug_dict.keys():
                rowDict[key] = debug_dict[key]
            outfiles[title(scenario)].writerow(rowDict)
            completed_dp += 1
            if int(100*completed_dp/total_dp) > completed_dp_percent:
                completed_dp_percent = int(100*completed_dp/total_dp)
                print('Completed %d%%' % completed_dp_percent)
        pool.close()
    except Exception as e:
        print("Exception")
        print(e)
        pool.terminate()
        pool.join()
    return

def schedStudySingleScenarioUtilUnpack(in_data: Tuple[Dict[str,str], float, int, int]) -> (Dict[str,str],
                                                                                           float,
                                                                                           Dict[int,float],
                                                                                           float,
                                                                                           float,
                                                                                           float,
                                                                                           int,
                                                                                           Dict[str,int]):
    scenario, sysutil, numCores, corePerComplex = in_data
    return schedStudySingleScenarioUtil(scenario, numCores, corePerComplex, sysutil)

_FAIL_THRESHOLD = 3
#                       optimal    infeas   infeas_unbound  unbound iter_limit  time_limit
_EXPECTED_STATUS_SET = [GRB.OPTIMAL, GRB.INFEASIBLE, GRB.INF_OR_UNBD, GRB.UNBOUNDED, GRB.ITERATION_LIMIT, GRB.TIME_LIMIT]

def interpretGurobiStatus(status:int) -> str:
    if status is GRB.INFEASIBLE:
        return 'NUM_INFEASIBLE'
    if status is GRB.INF_OR_UNBD:
        return 'NUM_INF_UB'
    if status is GRB.UNBOUNDED:
        return 'NUM_UNBOUNDED'
    if status is GRB.ITERATION_LIMIT:
        return 'NUM_ITER_LIMIT'
    if status is GRB.TIME_LIMIT:
        return 'NUM_TIMEOUT'
    #got unexpected status
    assert False

def schedStudySingleScenarioUtil(scenario,numCores,corePerComplex,sysUtil) -> (Dict[str,str],
                                                                               float,
                                                                               Dict[int,float],
                                                                               float,
                                                                               float,
                                                                               float,
                                                                               int,
                                                                               Dict[str,int]):
    # assuming task sets are generated on the fly, otherwise read from csv file by loadSystem if pre-generated
    # assuming a TaskSystem object is returned

    numSamples = 0
    sched_ratio_dict = {Constants.NO_THREAD: 0, Constants.THREAD_COURSE: 0, Constants.THREAD_FINE: 0}
    debug_dict = {}
    if Constants.DEBUG:
        for fr in failureReasons:
            debug_dict[fr] = 0

    numTasksAverage = 0
    timeAverage = 0

    numFails = sum([ 1 if failed else 0 for failed in failureDict[title(scenario)].values()])
    #No point if previous were unable to schedule
    #Note that this may cause false negatives if threads run waaaay out of order, but that's incredibly unlikely
    if numFails >= _FAIL_THRESHOLD:
        return scenario, sysUtil, sched_ratio_dict, numTasksAverage, timeAverage, 0, numSamples, debug_dict

    start_dp = time.clock()
    while numSamples < Constants.MIN_SAMPLES or normal_approx_error(sched_ratio_dict, numSamples):
        if numSamples >= Constants.MAX_SAMPLES:
            break
        start_iteration = time.clock()
        this_iter_results = {}
        # assume schedulable until something fails
        for scheme in sched_ratio_dict.keys():
            this_iter_results[scheme] = True

        if not Constants.RUN_FINE:
            this_iter_results[Constants.THREAD_FINE] = False

        if Constants.TIMEKEEPING:
            generate_start = time.clock()
        scenSystem = generateTaskSystem(scenario, sysUtil)
        # Replicate the task system so that one can be considered without threading
        cloneSystem = cloneTaskSystem(scenSystem)

        if Constants.TIMEKEEPING:
            print('TIME,Task_Sys,%d' % int(time.clock() - generate_start))

        if Constants.TIMEKEEPING:
            assign_start = time.clock()
        gStatus = scenSystem.levelA.setPairsList()
        assert( gStatus in _EXPECTED_STATUS_SET )
        if gStatus is not GRB.OPTIMAL:
            this_iter_results[Constants.THREAD_FINE] = this_iter_results[Constants.THREAD_COURSE] = False
            if Constants.DEBUG:
                debug_dict['A_MAKEPAIR_' + interpretGurobiStatus(gStatus)] += 1

        if this_iter_results[Constants.THREAD_COURSE] or this_iter_results[Constants.THREAD_FINE]:
            if not scenSystem.levelA.assignToCores(alg=Constants.WORST_FIT,
                                                   coreList=scenSystem.platform.coreList, dedicatedIRQ=True):
                this_iter_results[Constants.THREAD_FINE] = this_iter_results[Constants.THREAD_COURSE] = False
                if Constants.DEBUG:
                    debug_dict['NUM_PARTITION_THREAD_A'] += 1

        if this_iter_results[Constants.THREAD_FINE] or this_iter_results[Constants.THREAD_COURSE]:
            gStatus = scenSystem.levelB.setPairsList()
            assert( gStatus in _EXPECTED_STATUS_SET )
            if gStatus is not GRB.OPTIMAL:
                this_iter_results[Constants.THREAD_COURSE] = this_iter_results[Constants.THREAD_FINE] = False
                if Constants.DEBUG:
                    debug_dict['B_MAKEPAIR_'+interpretGurobiStatus(gStatus)] += 1

        if this_iter_results[Constants.THREAD_COURSE] or this_iter_results[Constants.THREAD_FINE]:
            if not scenSystem.levelB.assignToCores(alg=Constants.WORST_FIT,
                                               coreList=scenSystem.platform.coreList, dedicatedIRQ=True):
                this_iter_results[Constants.THREAD_COURSE] = this_iter_results[Constants.THREAD_FINE] = False
                if Constants.DEBUG:
                    debug_dict['NUM_PARTITION_THREAD_B'] += 1

        if this_iter_results[Constants.THREAD_FINE] or this_iter_results[Constants.THREAD_COURSE]:
            scenSystem.levelC.decideThreaded()
            if not scenSystem.levelC.divideCores(scenSystem.platform.coreList, corePerComplex, dedicatedIRQ=True):
                this_iter_results[Constants.THREAD_FINE] = this_iter_results[Constants.THREAD_COURSE] = False
                if Constants.DEBUG:
                    debug_dict['NUM_DIVIDE_CORES_C_THREAD'] += 1

        if this_iter_results[Constants.THREAD_FINE] or this_iter_results[Constants.THREAD_COURSE]:
            scenSystem.levelC.assignClusterID()
            scenSystem.levelC.assignClustersToCoreComplex(scenSystem.platform.complexList, corePerComplex)

            if not scenSystem.levelC.assignTasksToClusters():
                this_iter_results[Constants.THREAD_FINE] = this_iter_results[Constants.THREAD_COURSE] = False
                if Constants.DEBUG:
                    debug_dict['NUM_ASSIGN_CLUSTERS_C_THREAD'] += 1

        cloneSystem.levelA.setAllSolo()
        if not cloneSystem.levelA.assignToCores(alg=Constants.WORST_FIT,
                                                coreList=cloneSystem.platform.coreList, dedicatedIRQ=True):
            this_iter_results[Constants.NO_THREAD] = False
            if Constants.DEBUG:
                debug_dict['NUM_PARTITION_NO_THREAD_A'] += 1

        if this_iter_results[Constants.NO_THREAD]:
            cloneSystem.levelB.setAllSolo()
            if not cloneSystem.levelB.assignToCores(alg=Constants.WORST_FIT,
                                                coreList=cloneSystem.platform.coreList, dedicatedIRQ=True):
                this_iter_results[Constants.NO_THREAD] = False
                if Constants.DEBUG:
                    debug_dict['NUM_PARTITION_NO_THREAD_B'] += 1

        if this_iter_results[Constants.NO_THREAD]:
            cloneSystem.levelC.setAllSolo()
            if not cloneSystem.levelC.divideCores(cloneSystem.platform.coreList, corePerComplex, dedicatedIRQ=True):
                this_iter_results[Constants.NO_THREAD] = False
                if Constants.DEBUG:
                    debug_dict['NUM_DIVIDE_CORES_C_NO_THREAD'] += 1

            cloneSystem.levelC.assignClusterID()
            cloneSystem.levelC.assignClustersToCoreComplex(cloneSystem.platform.complexList, corePerComplex)

        if this_iter_results[Constants.NO_THREAD]:
            if not cloneSystem.levelC.assignTasksToClusters():
                this_iter_results[Constants.NO_THREAD] = False
                if Constants.DEBUG:
                    debug_dict['NUM_ASSIGN_CLUSTERS_C_NO_THREAD'] += 1

        if Constants.TIMEKEEPING:
            print('TIME,Assign_Tasks,%d' % int(time.clock() - assign_start))

        if Constants.TIMEKEEPING:
            optimize_start = time.clock()

        if any(this_iter_results.values()):
            overhead = Overheads()
            overhead.loadOverheadData('oheads')
            taskCount = len(scenSystem.levelA.tasksThisLevel) + len(scenSystem.levelB.tasksThisLevel) + len(
                scenSystem.levelC.tasksThisLevel)
            overhead.populateOverheadValue(taskCount=taskCount, allCriticalityLevels=scenSystem.levels)

        solver = LLCAllocation()
        if this_iter_results[Constants.NO_THREAD]:
            for curr_complex in cloneSystem.platform.complexList:
                if this_iter_results[Constants.NO_THREAD]:
                    gStatus = solver.coreWiseAllocation(cloneSystem, 16, overhead, curr_complex, len(curr_complex.coreList),
                                                      True,
                                                      cloneSystem.platform.coreList[0])
                    if gStatus is not GRB.OPTIMAL:
                        this_iter_results[Constants.NO_THREAD] = False
                        if Constants.DEBUG:
                            debug_dict['NO_THREAD_CACHE_ILP_' + interpretGurobiStatus(gStatus)] += 1
                        break
                else:
                    break

        if this_iter_results[Constants.THREAD_FINE] or this_iter_results[Constants.THREAD_COURSE]:
            # mySystem.platform.complexList[1].clusterList = [] #check if can handle empty cluster
            # solver.threadWiseAllocation(mySystem, 8, overhead, mySystem.platform.complexList[1], coresPerComplex, True, mySystem.platform.coreList[0])
            for curr_complex in scenSystem.platform.complexList:
                if this_iter_results[Constants.THREAD_FINE]:
                        gStatus = solver.threadWiseAllocation2(scenSystem, 16, overhead, curr_complex, len(curr_complex.coreList),
                                                        True,
                                                        scenSystem.platform.coreList[0])
                        if gStatus is not GRB.OPTIMAL:
                            this_iter_results[Constants.THREAD_FINE] = False
                            if Constants.DEBUG:
                                debug_dict['FINE_CACHE_ILP_' + interpretGurobiStatus(gStatus)] += 1
                        break
                if this_iter_results[Constants.THREAD_COURSE]:
                        gStatus = solver.coreWiseAllocation(scenSystem, 16, overhead, curr_complex, len(curr_complex.coreList),
                                                      True,
                                                      scenSystem.platform.coreList[0])
                        if gStatus is not GRB.OPTIMAL:
                            this_iter_results[Constants.THREAD_COURSE] = False
                            if Constants.DEBUG:
                                debug_dict['COURSE_CACHE_ILP_' + interpretGurobiStatus(gStatus)] += 1
                        break


        if Constants.TIMEKEEPING:
            print('TIME,Optimize_Cache,%d' % int(time.clock() - optimize_start))

        numSamples += 1
        for scheme in sched_ratio_dict.keys():
            sched_ratio_dict[scheme] *= (numSamples - 1) / numSamples
            sched_ratio_dict[scheme] += this_iter_results[scheme] / numSamples
        numTasksAverage *= (numSamples-1)/numSamples
        numTasksAverage += sum([len(crit_level.tasksThisLevel) for crit_level in scenSystem.levels.values()])/numSamples
        timeAverage *= (numSamples-1)/numSamples
        timeAverage += (time.clock() - start_iteration)/numSamples

    # todo: for this sysUtil write sched ratios to file
    if Constants.VERBOSE:
        print('COUNT,Scenario_Samples,%d' % numSamples)
    totalTime = time.clock() - start_dp
    return scenario, sysUtil, sched_ratio_dict, numTasksAverage, timeAverage, totalTime, numSamples, debug_dict


# Track how many 0 schedulability system utilization points we've tested for the given scenario
failureDict: Dict[str, Dict[float,bool]] = {}
failureReasons = []

def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('-d', "--datafile", type = argparse.FileType('w'),
    # default = sys.stdout,
    # help = "File to output csv file to")
    parser.add_argument('-m', "--processors", default=Constants.NUM_CORES, type=int, help="Number of cores")
    parser.add_argument('-c', "--corePerComplex", default=Constants.CORES_PER_COMPLEX, type=int, help="Number of cores per complex")
    parser.add_argument('-t', "--timekeeping", action='store_true', help="Track time spent")
    parser.add_argument('-v', "--verbose", action='store_true', help="Output print statements")
    parser.add_argument('-d', "--debug", action='store_true', help="Debug output")
    parser.add_argument('-f', "--fine_omit", action='store_true', help="Skip running the fine way allocation scheme")
    args = parser.parse_args()
    numCores = args.processors
    corePerComplex = args.corePerComplex

    if args.timekeeping:
        Constants.TIMEKEEPING = True
    if args.verbose:
        Constants.VERBOSE = True
    if args.debug:
        Constants.DEBUG = True
    if args.fine_omit:
        Constants.RUN_FINE = False

    startUtil = numCores / 2
    endUtil = 2 * numCores

    scenarios = generateScenario()

    dp = []
    #output
    outfiles = {}
    schemes = ['NO_THREAD', 'THREAD_FINE', 'THREAD_COURSE']
    fieldnames = ['SYS_UTIL'] + schemes
    fieldnames.extend(['NUM_SAMPLES', 'NUM_TASKS_AVG', 'TIME_AVG', 'TIME_TOTAL'])
    if Constants.DEBUG:
        gurobi_fields = ['NUM_TIMEOUT', 'NUM_ITER_LIMIT', 'NUM_INFEASIBLE', 'NUM_UNBOUNDED', 'NUM_INF_UNB']
        for optProblem in ['A_MAKEPAIR', 'B_MAKEPAIR', 'NO_THREAD_CACHE_ILP', 'FINE_CACHE_ILP','COURSE_CACHE_ILP']:
            failureReasons.extend([optProblem + '_' + gf for gf in gurobi_fields])
        for threadChoice in ['THREAD','NO_THREAD']:
            for level in ['A','B']:
                failureReasons.append('_'.join(['NUM_PARTITION',threadChoice,level]))
            failureReasons.append('NUM_DIVIDE_CORES_C_' + threadChoice)
            failureReasons.append('NUM_ASSIGN_CLUSTERS_C_' + threadChoice)
        fieldnames.extend(failureReasons)

    for scenario in scenarios:
        outfiles[title(scenario)] = DictWriter(open('results/' + title(scenario), 'w'),
                                               fieldnames=fieldnames)

        outfiles[title(scenario)].writeheader()
        failureDict[title(scenario)] = dict([ (util, False) for util in np.arange(startUtil, endUtil + Constants.UTIL_STEP_SIZE, Constants.UTIL_STEP_SIZE)])
        #for sysUtil in np.arange(startUtil, endUtil + Constants.UTIL_STEP_SIZE, Constants.UTIL_STEP_SIZE):
        for sysUtil in [7]: #np.arange(startUtil, endUtil + Constants.UTIL_STEP_SIZE, Constants.UTIL_STEP_SIZE):
            dp.append((scenario, sysUtil, numCores, corePerComplex))
    #if Constants.DEBUG:
    #    seq_dps(dp, outfiles)
    #else:
    #    thread_dps(dp, outfiles)
    #thread_dps(dp, outfiles)
    seq_dps(dp, outfiles)

    return

if __name__ == '__main__':
    main()