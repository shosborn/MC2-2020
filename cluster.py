from constants import Constants


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
        newUsedCapacity = self.usedCapacity + newTask.currentThreadedUtil
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
                print("Failed first test.")
                return False
            # secondTest
            sortedTasks = sorted(tempTaskList, key=lambda x: x.currentThreadedUtil, reverse=True)
            sumLargest = 0
            for t in range(min(m, len(self.taskList))):
                sumLargest = sumLargest + sortedTasks[t].currentThreadedUtil
            if (m - 1) * sortedTasks[0].currentThreadedUtil + sumLargest + self.usedCapacityHigherLevels >= m:
                print("Failed second test.")
                print("Single largest=", sortedTasks[0].currentThreadedUtil)
                print("sumLargest=", sumLargest)
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
            self.remainingCapacity = self.remainingCapacity - newTask.currentThreadedUtil
            self.usedCapacity = self.usedCapacity + newTask.currentThreadedUtil
        self.taskList.append(newTask)

    def schedTestNoOverheads(self):
        '''
        Makes the following assumptions:
        --w/n each criticality level, all cores have the same cache allocation
        --per Micaiah, don't need individual utilizations for A and B tasks; need totals only
        '''
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
