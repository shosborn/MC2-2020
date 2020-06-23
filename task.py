# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 16:53:35 2020

@author: simsh
"""

from constants import Constants
from typing import Dict
import math

class Task:

    _EXP_TOLERANCE: float = 1e-6

    def __init__(self, ID: int, taskLevel: int, baseCost: float, period: int, relDeadline: int,
                 wss: float, cache_sense: float, crit_scale_dict: Dict[int, float]):
        self.ID: int =ID
        self.period: int = period
        self.relDeadline: int = relDeadline
        self.baseCost: float = baseCost
        #order of indexing is sibling task ID, MY number of ways half ways, crit level, sibling's number of half ways
        self.allUtil: Dict[int,Dict[int,Dict[int,float]]] = {}
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
        self._per_cache_crit_costs: Dict[int, Dict[int, float]] = {}
        self._generate_per_cache_crit_costs(cache_sense, crit_scale_dict)

    def _generate_per_cache_crit_costs(self, cache_sense: float, crit_scale_dict: Dict[int,float]):
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
            self._per_cache_crit_costs[half_ways] = {}
            self._per_cache_crit_costs[half_ways][self.level] = baseCostWays
            # compute costs at lower crit levels
            for level in crit_scale_dict.keys():
                assert(level >= self.level)
                if level is self.level:
                    #We've already generated this above
                    continue
                #Need to divide by scaling at our current level to get back to Level-A pessimism, then scale
                #   back down to the lower level
                self._per_cache_crit_costs[half_ways][level] = \
                    baseCostWays*crit_scale_dict[level]/crit_scale_dict[self.level]

    def deflate(self, deflation_factor: float):
        assert( 0 < deflation_factor < 1)
        for half_ways in self._per_cache_crit_costs.keys():
            per_crit_costs = self._per_cache_crit_costs[half_ways]
            for level in per_crit_costs.keys():
                per_crit_costs[level] *= deflation_factor

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
        #we should never request a task's cost for any level higher than its own
        assert(level >= self.level)
        return self._per_cache_crit_costs[cache_half_ways][level]