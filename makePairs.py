# -*- coding: utf-8 -*-
"""
Copyright 2020 Sims Hill Osborne, 2021 Joshua Bakita

Created on Thu Oct 17 08:53:41 2019
"""

from gurobipy import *
import numpy as np

import task
from constants import Constants

from typing import Tuple

# Runtime constants for Gurobi
TIMEOUT = 60 # Seconds
SOLUTION_LIMIT=1000
THREADS_PER_TEST = 0 # 0 is a special value which tells Gurobi to auto-determine

class MakePairsILP:
    #create variables for frame sizes
    def __init__(self, curSystem):
        self.solver=Model()
        # Silence Gurobi output
        self.solver.setParam("OutputFlag", False)
        self.curSystem = curSystem
        # print("Printing tasksThisLevel")
        # print(curSystem.tasksThisLevel)
        self.startingTaskID=curSystem.tasksThisLevel[0].ID
        self.schedVarsP = None
        self.threadedUtil = None

    def makePairs(self) -> (Tuple[int,int,float], float, int):
        self.setSolverParams()
        #print("completed setSolverParams")
        self.schedVarsP=self.createSchedVarsAndSetObj()
        #print("completed createdSchedVars")
        self.requireAllJobsScheduled()
        #print("completed requireAllJobsScheduled")
        self.solver.optimize()
        #print("completed optimize.")
        #print(self.schedVarsP)

        #Return a list showing all pairs
        #Note some items are paired with themselves
        curSystem=self.curSystem

        #fix i values here

        thePairs = []
        for k in range(len(self.schedVarsP)):
            if self.schedVarsP[k]['schedVar'].x == 1:
                i = self.schedVarsP[k]['taskID_1']
                j = self.schedVarsP[k]['taskID_2']
                task_i = self.curSystem.tasksThisLevel[i - self.startingTaskID]
                task_j = self.curSystem.tasksThisLevel[j - self.startingTaskID]
                pairUtil = task.get_pair_util(task_i, task_j, curSystem.level,
                                             curSystem.assumedCache // Constants.SIZE_OF_HALF_WAYS // 2,
                                             curSystem.assumedCache // Constants.SIZE_OF_HALF_WAYS // 2)

                # Place the heavier task on the even thread
                if task_i.baseCost > task_j.baseCost:
                    thisPair = (i, j, float(pairUtil))
                else:
                    thisPair = (j, i, float(pairUtil))
                thePairs.append(thisPair)

        return thePairs, self.solver.runtime, self.solver.status

    def setSolverParams(self):
        self.solver.setParam("TimeLimit", TIMEOUT)
        self.solver.setParam("SolutionLimit", SOLUTION_LIMIT)
        self.solver.setParam(GRB.Param.Threads, THREADS_PER_TEST)

    def createSchedVarsAndSetObj(self):
        taskSystem=self.curSystem
        tasksThisLevel=taskSystem.tasksThisLevel

        numTasks = len(tasksThisLevel)
        # numConfigs upper bounds the number of configs we'll store (as periods may not match)
        numConfigs = (numTasks**2 - numTasks) // 2 + numTasks 
        # Use a structured array for space efficiency and locality
        schedVars = np.zeros(numConfigs, dtype={'names':('taskID_1', 'taskID_2', 'schedVar'), 'formats':(np.dtype(int), np.dtype(int), np.dtype(object))})

        expr=LinExpr()
        # range for i needs to start at the correct point

        # startingTaskID=tasksThisLevel[0].ID
        # startingTaskID=1
        nextIdx = 0
        for i in range(0, len(tasksThisLevel)):
            for j in range(i, len(tasksThisLevel)):
                task1 = tasksThisLevel[i]
                task2 = tasksThisLevel[j]
                periodsMatch=(task1.period==task2.period)
                #this part of program only runs once, with an assumed cache level
                '''
                print()
                print("Printing taskID and costs.")
                print(myTask.ID)
                print(myTask.allUtil)
                print()
                '''
                #pairedCost=system.tasksThisLevel[i].allCosts[(j, system.level, system.assumedCache)]
                pairedUtil = task.get_pair_util(task1, task2, taskSystem.level,
                                                taskSystem.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,
                                                taskSystem.assumedCache//Constants.SIZE_OF_HALF_WAYS//2
                )

                if periodsMatch and pairedUtil <= Constants.MAX_THREADED_UTIL:
                    var = self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    schedVars[nextIdx]['taskID_1'] = i + self.startingTaskID
                    schedVars[nextIdx]['taskID_2'] = j + self.startingTaskID
                    schedVars[nextIdx]['schedVar'] = var
                    nextIdx += 1
                    expr += var * pairedUtil

        self.threadedUtil=self.solver.addVar(vtype=GRB.CONTINUOUS)
        self.solver.setObjective(self.threadedUtil, GRB.MINIMIZE)
        self.solver.addConstr(lhs=self.threadedUtil, rhs=expr, sense=GRB.EQUAL)

        # Return scheduling vars after trimming rows with non-valid IDs
        # (numConfigs may have overprovisioned the array size)
        return schedVars[schedVars['taskID_1'] != 0]

    def requireAllJobsScheduled(self):
        system=self.curSystem
        # For every task
        for taskID in range(self.startingTaskID, self.startingTaskID + len(system.tasksThisLevel)):
            # Get any sched vars where this task is taskID_1 or taskID_2 (all pairs that include this task)
            schedVarsThisTask = self.schedVarsP[((self.schedVarsP['taskID_1'] == taskID) |
                                                 (self.schedVarsP['taskID_2'] == taskID))]['schedVar']
            # Require that at least one of the pairs including this taskID is scheduled
            # (It can be scheduled with itself - this indicates no pairing.)
            expr = LinExpr()
            for schedVar in schedVarsThisTask:
                expr += schedVar
            self.solver.addConstr(lhs=expr, rhs=1, sense=GRB.EQUAL)
'''
def main():
    from taskSystem import taskSystem
    #from crit_level import CritLevel
    #from constants import Constants

    totalCores=4
    coresPerComplex=4
    cacheSizeL3=2

    assumedCache=cacheSizeL3

    fileLevelA="levelA-v1.csv"
    mySystem=taskSystem(totalCores, coresPerComplex, cacheSizeL3, assumedCache, fileLevelA)
    mySystem.levelA.loadSystem(fileLevelA)
    mySystem.levelA.setPairsList()
'''

#if __name__== "__main__":
#     main()

