import random
import math

from constants import Constants
from crit_level import CritLevelSystem
from task import Task
from taskSystem import taskSystem

def uniform(min, max):
    return random.uniform(min, max)

def discreteUniform(choices):
    return choices[random.randint(0,len(choices)-1)]

class TaskSystemGenerator:
    def __init__(self, critUtilDist, periodDist, taskUtil, maxUtil, assumedCache):
        self.critUtilDist = Constants.CRITICALITY_DIST[critUtilDist]
        self.periodDist = Constants.PERIOD_DIST[periodDist]
        self.taskUtil = Constants.TASK_UTIL[taskUtil]

        self.normalizedUtil = []
        for critLevel in range(Constants.LEVEL_A,Constants.LEVEL_C+1):
            percentageOfTasks = uniform(self.critUtilDist[Constants.LEVEL_A][0], self.critUtilDist[Constants.LEVEL_A][1])
            self.normalizedUtil.append(percentageOfTasks)
        self.normalizedUtil /= sum(ratio for ratio in self.normalizedUtil) * maxUtil

        self.startingTaskID = [0,0,0]
        self.assumedCache = assumedCache #do we need assumedCache here?


    def generateCritLevelTaskSystem(self, critLevelSystem, utilDist, periodDist, maxUtil):

        #todo: (important) which util this will be? Task has a lot of utils depending on pairing and allocated cache size
        curUtil = 0
        assumedCache = self.assumedCache #move this out to constants.py
        critLevel = critLevelSystem.level
        startingTaskID = self.startingTaskID[critLevel]
        critLevelSystem = CritLevelSystem(critLevel,assumedCache)
        while curUtil < maxUtil:
            util = uniform(utilDist[0],utilDist[1])
            if critLevel <= Constants.LEVEL_B:
                period = discreteUniform(periodDist)
            else:
                period = uniform(periodDist[0],periodDist[1])

            task = Task(startingTaskID, critLevel, period, period)
            critLevelSystem.tasksThisLevel.append(task)

            curUtil += util

        return critLevelSystem

    def generateTaskSystem(self, numCores, corePerComplex, cacheSize):
        newTaskSystem = taskSystem(totalcores=numCores, coresPerComplex=corePerComplex, )
        for critLevelSystem in newTaskSystem.levels:
            critLevel = critLevelSystem.level
            utilDist = self.critUtilDist[critLevel]
            periodDist = self.periodDist[critLevel]
            maxUtil = self.normalizedUtil[critLevel]
            self.generateCritLevelTaskSystem(critLevelSystem, utilDist, periodDist, maxUtil)

        return newTaskSystem




def main():
    random.seed(1234)
    for i in range(0,10):
        print(discreteUniform((1,2,3,4,5,6)))
    return

if __name__ == '__main__':
    main()