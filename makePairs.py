# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 08:53:41 2019

@author: shosborn
"""

from gurobipy import *
#from random import random, gauss, uniform, choice
import pandas as pd

import task
from constants import Constants

from typing import Tuple


TIMEOUT=60
SOLUTION_LIMIT=1000
#0 threds per test --> let Gurobi figure out how many to use
THREADS_PER_TEST=0

#index values for returned tuples
TASK1=0
TASK2=1
PERIOD=2
UTIL=3

class MakePairsILP:
    #create variables for frame sizes
    
    def __init__(self, curSystem):
        self.solver=Model()
        self.solver.setParam("OutputFlag", False)
        #self.solver.getEnv().set(GRB_IntParam_OutputFlag, 0)
        self.curSystem=curSystem
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
        
        thePairs=[]
        for k in range(len(self.schedVarsP.index)):
            if self.schedVarsP['schedVar'].iloc[k].x==1:
                i=self.schedVarsP['taskID_1'].iloc[k]
                j=self.schedVarsP['taskID_2'].iloc[k]
                task_i = self.curSystem.tasksThisLevel[i - self.startingTaskID]
                task_j = self.curSystem.tasksThisLevel[j - self.startingTaskID]
                #pairPeriod=curSystem.tasksThisLevel[i].period
                pairUtil= task.get_pair_util(task_i, task_j, curSystem.level,
                                             curSystem.assumedCache//Constants.SIZE_OF_HALF_WAYS//2,
                                             curSystem.assumedCache//Constants.SIZE_OF_HALF_WAYS//2
                )
                #self.curSystem.tasksThisLevel[i-self.startingTaskID].allUtil[(j,
                #                                               curSystem.level,
                #                                               curSystem.assumedCache)]

                #Place the heavier task on the even thread
                if task_i.baseCost > task_j.baseCost:
                    thisPair=(i, j, float(pairUtil))
                else:
                    thisPair=(j, i, float(pairUtil))
                thePairs.append(thisPair)

        return thePairs, self.solver.runtime, self.solver.status
    

    def setSolverParams(self):
        self.solver.setParam("TimeLimit", TIMEOUT)
        self.solver.setParam("SolutionLimit", SOLUTION_LIMIT)
        self.solver.setParam(GRB.Param.Threads, THREADS_PER_TEST)
        


    def createSchedVarsAndSetObj(self):
        taskSystem=self.curSystem
        tasksThisLevel=taskSystem.tasksThisLevel
        
        schedVars={'taskID_1'      : [],
                        'taskID_2'      : [],
                        'schedVar'   : []
                }

        expr=LinExpr()
        # range for i needs to start at the correct point

        # startingTaskID=tasksThisLevel[0].ID
        # startingTaskID=1
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

                if periodsMatch and pairedUtil<= Constants.MAX_THREADED_UTIL:
                
                    #pairedUtil=pairedCost/tasksThisLevel[i].period
                    var=self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    #problem is here; I'm giving tasks the wrong IDs
                    schedVars['taskID_1'].append(i+self.startingTaskID)
                    schedVars['taskID_2'].append(j+self.startingTaskID)
                    schedVars['schedVar'].append(var)

                    expr += var * pairedUtil
        
        self.threadedUtil=self.solver.addVar(vtype=GRB.CONTINUOUS)
        self.solver.setObjective(self.threadedUtil, GRB.MINIMIZE)
        self.solver.addConstr(lhs=self.threadedUtil, rhs=expr, sense=GRB.EQUAL)
        
        #return scheduling vars for future use
        return pd.DataFrame(schedVars)
        
        
        
               
    def requireAllJobsScheduled (self):
        system=self.curSystem
        for i in range(len(system.tasksThisLevel)):
            schedVarsThisTask=self.schedVarsP[(self.schedVarsP['taskID_1']==i+self.startingTaskID) | 
                    (self.schedVarsP['taskID_2']==i + self.startingTaskID) ]
            expr=LinExpr()
            for k in range(len(schedVarsThisTask.index)):
                expr += schedVarsThisTask['schedVar'].iloc[k]
            #for every i, paired with exactly one other (include itself as an option)
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
        

 
