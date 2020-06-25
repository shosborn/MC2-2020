# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 16:53:35 2020

@author: simsh
"""

from constants import Constants
from typing import Dict, Tuple
import math

import numpy as np



class Task:

    _EXP_TOLERANCE: float = 1e-6

    def __init__(self, ID: int, taskLevel: int, baseCost_ms: float, period_ms: int, relDeadline_ms: int,
                 wss: float, cache_sense: float, crit_scale_dict: Dict[int, float], levelFirstID: int):
        self.ID: int =ID
        self.period: int = 1000*period_ms
        self.relDeadline: int = 1000*relDeadline_ms
        self.baseCost: float = 1000*baseCost_ms
        #necessary to index into allUtil_AB
        self.startingID = levelFirstID
        #order of indexing is sibling task ID, MY number of half ways, crit level, sibling's number of half ways
        #This data structure assumes self is not sibling and that both are AB tasks
        #This data structure is not exposed outside of task generation. Use get_pair_util.
        #self.allUtil_AB: Dict[Tuple[int, int, int, int], float] = {}
        #need to know the crit level size before we can initialize this
        self.allUtil_AB: np.ndarray = None
        #order of indexing is number of half ways, crit level
        #self.allUtil_C: Dict[Tuple[int, int], float] = {}
        self.allUtil_C: np.ndarray = np.empty([Constants.MAX_HALF_WAYS+1,Constants.MAX_LEVEL], dtype=float)
        self.level: int = taskLevel
        if taskLevel == Constants.LEVEL_C:
            self.currentSoloUtil=0
            self.currentThreadedCost = 0
            self.currentThreadedUtil = 0
        # wss is in MB
        # 2020 platform has ways of 1MB each
        # half-ways of 512 KB each.
        self.wss = wss
        self.wss_in_half_ways = wss/Constants.SIZE_OF_HALF_WAYS
        #self._per_cache_crit_costs: Dict[int, Dict[int, float]] = {}
        self._per_cache_crit_costs: np.ndarray = np.empty([Constants.MAX_HALF_WAYS+1, Constants.MAX_LEVEL], dtype=float)
        self._generate_per_cache_crit_costs(cache_sense, crit_scale_dict)

    def _generate_per_cache_crit_costs(self, cache_sense: float, crit_scale_dict: Dict[int,float]) -> None:
        #First generate the inverse exponential curve that corresponds to costs at our crit level
        cost_no_cache = self.baseCost*cache_sense
        #Having less cache should not improve cost
        assert(cost_no_cache > self.baseCost)
        #The following function returns cost_no_cache at 0 half ways, never decreases beyond baseCost, and is
        #   around _EXP_TOLERANCE of baseCost for any number of half ways >= wss in half ways
        #First need to solve for the rate parameter of the inverse exponential
        rate = -math.log(Task._EXP_TOLERANCE/(cost_no_cache - self.baseCost), math.e)/self.wss_in_half_ways
        cost_func = lambda _half_ways: (cost_no_cache - self.baseCost)*math.exp(-rate*_half_ways) + self.baseCost
        assert(math.fabs(cost_func(self.wss_in_half_ways) - self.baseCost) <= 2*Task._EXP_TOLERANCE)
        for half_ways in range(Constants.MAX_HALF_WAYS+1):
            # compute costs at our crit level
            baseCostWays = cost_func(half_ways)
            #self._per_cache_crit_costs[half_ways] = {}
            #self._per_cache_crit_costs[half_ways][Constants.LEVEL_A] = baseCostWays
            self._per_cache_crit_costs[half_ways,Constants.LEVEL_A] = baseCostWays
            # compute costs at lower crit levels
            for level in crit_scale_dict.keys():
                if level is Constants.LEVEL_A:
                    #just computed this
                    continue
                #Need to divide by scaling at our current level to get back to Level-A pessimism, then scale
                #   back down to the lower level
                #self._per_cache_crit_costs[half_ways][level] = \
                #    baseCostWays*crit_scale_dict[level]/crit_scale_dict[self.level]
                self._per_cache_crit_costs[half_ways,level] = \
                    baseCostWays*crit_scale_dict[level]/crit_scale_dict[self.level]

    def deflate(self, deflation_factor: float) -> None:
        assert( 0 < deflation_factor < 1)
        #for half_ways in self._per_cache_crit_costs.keys():
        #    per_crit_costs = self._per_cache_crit_costs[half_ways]
        #    for level in per_crit_costs.keys():
        #        per_crit_costs[level] *= deflation_factor
        for half_ways in range(Constants.MAX_HALF_WAYS+1):
            for level in range(Constants.MAX_LEVEL):
                self._per_cache_crit_costs[half_ways,level] *= deflation_factor

    def getWss(self):
        return self.wss / Constants.SIZE_OF_HALF_WAYS

    def __repr__(self):
        return "ID: %s"%self.ID

    def __srt__(self):
        return "ID: %s" % self.ID

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.ID == other.ID
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def cost_per_cache_crit(self, cache_half_ways: int, level: int) -> float:
        #should not request cache more than available or negative
        assert(0 <= cache_half_ways <= Constants.MAX_HALF_WAYS)
        #return self._per_cache_crit_costs[cache_half_ways][level]
        return self._per_cache_crit_costs[int(cache_half_ways),level]

    def initialize_smt_array_AB(self, num_tasks_level:int):
        self.allUtil_AB = np.empty([
            num_tasks_level,
            Constants.MAX_HALF_WAYS//2 + 1,
            Constants.MAX_LEVEL,
            Constants.MAX_HALF_WAYS//2 + 1
        ], dtype=float)

    def set_smt_util_AB(self, sibling: int, half_ways: int, level: int, half_ways_sibling: int, util:float):
        self.allUtil_AB[sibling - self.startingID, half_ways, level, half_ways_sibling] = util

    def set_smt_util_C(self, half_ways: int, level: int, util:float):
        self.allUtil_C[half_ways,level] = util


def get_pair_util(task1: Task, task2: Task, level: int, cache1: int, cache2: int) -> float:
    """
    It's important that this is used as intended. Cache amounts in cache1 and cache2 refer to
    cache amounts produced by an ILP. The actual cache allocation corresponding to cache1 and cache2
    may be double the smaller (solo task) or ignored entirely (cache2 when we are in Level-C)
    Unlike _allUtil, we account for when task1 == task2.
    :param task1: task
    :param task2: sibling task
    :param level: criticality level we are considering
    :param cache1:
    :param cache2:
    :return:
    """
    cache1 = int(cache1)
    if task1.level is Constants.LEVEL_C:
        if task1 is not task2:
            #Siblings are irrelevant in SMT costs at C
            #Assuming C is colorless, so we get the full way here
            #return task1.allUtil_C[(2*cache1,level)]
            return task1.allUtil_C[2*cache1,level]
        else:
            return task1.cost_per_cache_crit(2*cache1,level)/task1.period
    else: #Assume we're in A or B
        cache2 = int(cache2)
        if task1 is not task2:
            startingID = task1.startingID
            #should be true for tasks in same level
            assert(startingID == task2.startingID)
            #The larger within this container is the container's cost
            return max([
                #task1.allUtil_AB[(task2.ID,cache1,level,cache2)],
                task1.allUtil_AB[task2.ID-startingID,cache1,level,cache2],
                #task2.allUtil_AB[(task1.ID,cache2,level,cache1)]
                task2.allUtil_AB[task1.ID-startingID,cache2,level,cache1]
            ])
        else:
            #I'm solo, so I'm colorless and I get the whole way, but only the minimum of my two way sets
            return task1.cost_per_cache_crit(2*min([cache1,cache2]), level)/task1.period