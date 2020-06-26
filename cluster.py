from constants import Constants

from core import compCore

class Cluster:
    def __init__(self, coresThisCluster, threaded):
        self.coresThisCluster = coresThisCluster
        self.taskList = []
        # will change with cache allocations
        self.usedCapacityHigherLevels=0
        for c in coresThisCluster:
            self.usedCapacityHigherLevels=self.usedCapacityHigherLevels+c.utilOnCore[Constants.LEVEL_C]
        if threaded:
            self.usedCapacityHigherLevels=self.usedCapacityHigherLevels*2
            self.remainingCapacity=2*len(coresThisCluster)-self.usedCapacityHigherLevels
        else:
            self.remainingCapacity=len(coresThisCluster)-self.usedCapacityHigherLevels

        self.usedCapacity=self.usedCapacityHigherLevels
        self.threaded=threaded
        self.clusterID = 0

    def testAndAddTask(self, newTask):
        # adds newTask iff doing so won't make system unschedulable
        tempTaskList = self.taskList.copy()
        tempTaskList.append(newTask)
        newUsedCapacity = self.usedCapacity + (newTask.currentThreadedUtil if self.threaded else newTask.currentSoloUtil)
        if not self.threaded:
            #first test
            m=len(self.coresThisCluster)
            if newUsedCapacity>m:
                return False

            # second test
            sortedTasks = sorted(tempTaskList, key=lambda x: x.currentSoloUtil, reverse=True)
            sumLargest = 0
            for t in range(min(m, len(self.taskList))):
                sumLargest = sumLargest + sortedTasks[t].currentSoloUtil
            if (m - 1) * sortedTasks[0].currentSoloUtil + sumLargest + self.usedCapacityHigherLevels >= m:
                return False

            # if adding task will not make cluster unschedulable, go ahead and add it
            self.addTask(newTask)
            return True

        else:
            m=2*len(self.coresThisCluster)
            #first test
            if newUsedCapacity>m:
                #print("Failed first test.")
                return False
            # secondTest
            sortedTasks = sorted(tempTaskList, key=lambda x: x.currentThreadedUtil, reverse=True)
            sumLargest = 0
            for t in range(min(m, len(self.taskList))):
                sumLargest = sumLargest + sortedTasks[t].currentThreadedUtil
            if (m - 1) * sortedTasks[0].currentThreadedUtil + sumLargest + self.usedCapacityHigherLevels >= m:
                #print("Failed second test.")
                #print("Single largest=", sortedTasks[0].currentThreadedUtil)
                #print("sumLargest=", sumLargest)
                #print("sum largest + used HL=", (m - 1) * sortedTasks[0].currentThreadedUtil + sumLargest + self.usedCapacityHigherLevels )
                return False

            # if adding task will not make cluster unschedulable, go ahead and add it
            self.addTask(newTask)
            return True

    def addTask(self, newTask):
        if self.threaded:
            self.remainingCapacity=self.remainingCapacity-newTask.currentThreadedUtil
            self.usedCapacity=self.usedCapacity+newTask.currentThreadedUtil
        else:
            self.remainingCapacity = self.remainingCapacity - newTask.currentSoloUtil
            self.usedCapacity = self.usedCapacity + newTask.currentSoloUtil
        self.taskList.append(newTask)

    '''
    Makes the following assumptions:
    --w/n each criticality level, all cores have the same cache allocation
    --per Micaiah, don't need individual utilizations for A and B tasks; need totals only
    '''
    def schedTestNoOverheads(self):
        if not self.threaded:
            m=len(self.coresThisCluster)
            # test for total util
            if self.usedCapacity>m:
                return False

            # second test
            # sort tasks by non-ascending util
            sortedTasks = sorted(self.taskList, key=lambda x:x.currentSoloUtil, reverse=True)
            sumLargest=0
            for t in range(min(m, len(self.taskList))):
                sumLargest=sumLargest+sortedTasks[t].currentSoloUtil
            if (m-1)*sortedTasks[0].currentSoloUtil + sumLargest + self.usedCapacityHigherLevels>=m:
                return False
            return True

        else:
            m = 2*len(self.coresThisCluster)
            # test for total util
            if self.usedCapacity>m:
                return False

            # second test
            # sort tasks by non-ascending util
            sortedTasks = sorted(self.taskList, key=lambda x: x.currentThreadedUtil, reverse=True)
            sumLargest = 0
            for t in range(min(m, len(self.taskList))):
                #sumLargest = sumLargest + sortedTasks[t].currentSoloUtil #should be currentThrededUtil?
                sumLargest = sumLargest + sortedTasks[t].currentThreadedUtil
            if (m - 1) * sortedTasks[0].currentThreadedUtil + sumLargest + self.usedCapacityHigherLevels >= m:  #should be currentThrededUtil?
                return False
            return True

def compCluster(clus1: Cluster, clus2: Cluster):
    #self.coresThisCluster = coresThisCluster
    assert( len(clus1.coresThisCluster) is len(clus2.coresThisCluster) )
    for idx in range(len(clus1.coresThisCluster)):
        compCore(clus1.coresThisCluster[idx], clus2.coresThisCluster[idx])
    #self.taskList = []
    assert(len(clus1.taskList) is len(clus2.taskList))
    for task in clus1.taskList:
        assert(task in clus2.taskList)
    #self.usedCapacityHigherLevels = 0
    assert(-1e9 < clus1.usedCapacityHigherLevels - clus2.usedCapacityHigherLevels < 1e9)
    #for c in coresThisCluster:
    #    self.usedCapacityHigherLevels = self.usedCapacityHigherLevels + c.utilOnCore[Constants.LEVEL_C]
    assert(-1e9 < clus1.usedCapacityHigherLevels - clus2.usedCapacityHigherLevels < 1e9)
    assert(-1e9 < clus1.remainingCapacity - clus2.remainingCapacity < 1e9)
    assert(-1e9 < clus1.usedCapacity - clus2.usedCapacity < 1e9)
    assert(clus1.threaded is clus2.threaded)
    assert(clus1.clusterID is clus2.clusterID)
    #if threaded:
    #    self.usedCapacityHigherLevels = self.usedCapacityHigherLevels * 2
    #    self.remainingCapacity = 2 * len(coresThisCluster) - self.usedCapacityHigherLevels
    #else:
    #    self.remainingCapacity = len(coresThisCluster) - self.usedCapacityHigherLevels

    #self.usedCapacity = self.usedCapacityHigherLevels
    #self.threaded = threaded
    #self.clusterID = 0