# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 08:53:41 2019

@author: shosborn
"""

from gurobipy import *
from random import random, gauss, uniform, choice
import pandas as pd


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
        self.curSystem=curSystem

    
    def makePairs(self):
        self.setSolverParams()
        self.schedVarsP=self.createSchedVarsAndSetObj()
        self.requireAllJobsScheduled()
        self.solver.optimize()
        
        #Return a list showing all pairs
        #Note some items are paired with themselves
        curSystem=self.curSystem

        thePairs=[]
        for k in range(len(self.schedVarsP.index)):
            if self.schedVarsP['schedVar'].iloc[k].x==1:
                i=self.schedVarsP['taskID_1'].iloc[k]
                j=self.schedVarsP['taskID_2'].iloc[k]
                pairPeriod=curSystem.tasksThisLevel[i].period
                pairCost=self.curSystem.tasksThisLevel[i].allCosts[(j, 
                                                               curSystem.level, 
                                                               curSystem.assumedCache)]
                thisPair=(i, j, float(pairCost/pairPeriod))
                thePairs.append(thisPair)
        return (thePairs, self.solver.runtime)
    

        '''
        print("task1, task2")
        for k in range(len(self.schedVarsP.index)):
            if self.schedVarsP['schedVar'].iloc[k].x==1:
                print(self.schedVarsP['taskID_1'].iloc[k], self.schedVarsP['taskID_2'].iloc[k])

        '''

    def setSolverParams(self):
        self.solver.setParam("TimeLimit", TIMEOUT)
        self.solver.setParam("SolutionLimit", SOLUTION_LIMIT)
        self.solver.setParam(GRB.Param.Threads, THREADS_PER_TEST)
        


    def createSchedVarsAndSetObj(self):
        system=self.curSystem
        tasksThisLevel=system.tasksThisLevel
        
        schedVars={'taskID_1'      : [],
                        'taskID_2'      : [],
                        'schedVar'   : []
                }

        expr=LinExpr()
        # recall tasks are 0-indexed
        for i in range(0, len(tasksThisLevel)):
            for j in range(i, len(tasksThisLevel)):
                
                periodsMatch=(tasksThisLevel[i].period==tasksThisLevel[j].period)
                #this part of program only runs once, with an assumed cache level
                myTask=tasksThisLevel[i]
                #print(myTask.allCosts)
                #pairedCost=system.tasksThisLevel[i].allCosts[(j, system.level, system.assumedCache)]
                pairedCost=myTask.allCosts[(j, system.level, system.assumedCache)]
                
                if periodsMatch and pairedCost<=tasksThisLevel[i].period:
                
                    pairedUtil=pairedCost/tasksThisLevel[i].period
                    var=self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    schedVars['taskID_1'].append(i)
                    schedVars['taskID_2'].append(j)
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
            schedVarsThisTask=self.schedVarsP[(self.schedVarsP['taskID_1']==i) | (self.schedVarsP['taskID_2']==i) ]
            expr=LinExpr()
            for k in range(len(schedVarsThisTask.index)):
                expr += schedVarsThisTask['schedVar'].iloc[k]
            #for every i, paired with exactly one other (include itself as an option)
            self.solver.addConstr(lhs=expr, rhs=1, sense=GRB.EQUAL)

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
             
                
if __name__== "__main__":
     main()            
        

 
