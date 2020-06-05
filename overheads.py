from csv import DictReader
from collections import defaultdict
from constants import Constants
import pandas as pd


class Overheads:

    def __init__(self):
        self.overheadData = None

    def loadOverheadData(self,dirName):
        '''
        Load overhead data to self.overheadData after making the data monotonic
        :param dirName: directory where overhead data are stored
        :return:
        '''
        critMap = {'A':0, 'B': 1, 'C':2}
        overheadData = defaultdict()
        for critLevelKey  in critMap:
            critLevelValue = critMap[critLevelKey]
            overheadData[critLevelValue] = defaultdict()
            fileName = dirName + "//ovh_" + critLevelKey + "_mc2" + ".csv"
            overheadData[critLevelValue] = pd.read_csv(fileName, index_col=0)
            #print(overheadData[critLevelValue])
            for column in range(overheadData[critLevelValue].shape[1]):
                maxValue = -1
                for row in range(overheadData[critLevelValue].shape[0]):
                    maxValue = max(maxValue,overheadData[critLevelValue].iloc[row,column])
                    overheadData[critLevelValue].iloc[row, column] = maxValue #make monotonic
        self.overheadData = overheadData

    def montonicInterpolation(self,taskCount,criticalityLevel,overhead):
        '''
        interpolate overhead value of an overhead type for arbitrary task count from overhead data
        if task count is greater than the max task count in overhead data, then the value for max task count
        is returned, i.e., max overhead value in the data
        :param taskCount: number of tasks
        :param criticalityLevel: criticality level for overhead data
        :param overhead: overhead type, column header of csv file
        :return: interpolated value
        '''
        numTasks = list(self.overheadData[criticalityLevel].index)
        overheadData = self.overheadData[criticalityLevel][overhead]
        if taskCount < numTasks[0]:
            return overheadData.iloc[0]
        if taskCount > numTasks[-1]:
            return overheadData.iloc[-1]
        start = 0
        end = len(numTasks)-1
        mid = int(len(numTasks)/2)
        while numTasks[mid] != taskCount:
            if taskCount < numTasks[mid]:
                end = mid-1
            else:
                start = mid+1
            if start > end:
                break
            mid = int((start+end)/2)
        if numTasks[mid] == taskCount:
            return overheadData.iloc[mid]
        if numTasks[mid] > taskCount:
            return overheadData.iloc[mid-1] + (overheadData.iloc[mid]-overheadData.iloc[mid-1])/(numTasks[mid]-numTasks[mid-1])*\
                   (taskCount-overheadData.iloc[mid-1])
        if numTasks[mid] < taskCount:
            return overheadData.iloc[mid] + (overheadData.iloc[mid+1] - overheadData.iloc[mid]) / (
                        numTasks[mid+1] - numTasks[mid]) * \
                   (taskCount - overheadData.iloc[mid])

    def getOverheadValue(self,taskCount,criticalityLevel,overhead):
        '''
        get overhead value. currently for any overhead other than CPMD
        use list of tasks instead of taskCount (may be needed for CPMD)? otherwise for CPMD getCPMD() method can be called directly.
        :param taskCount: number of tasks
        :param overhead: overhead type for which value is derived
        :return:
        '''
        if overhead == 'CPMD': #cache related preemption and migration delay
            raise NotImplementedError
        # for any taskcount > max # of tasks in overhead data, maxmimum observed overhead value is used
        return self.montonicInterpolation(taskCount,criticalityLevel,overhead)

    def getCPMD(self,task,cacheSize):
        '''
        calculate cache related preemption and migration delay.
        wss is assumed to be stored in task.py
        todo: for level-A, -B, cachesize can be be found from its assigned core?
        :param task:
        :param cacheSize:
        :return:
        '''
        return
def main():
    overHeads = Overheads()
    overHeads.loadOverheadData('oheads')
    value = overHeads.montonicInterpolation(75,0,'CXS')
    print(value)
    return

if __name__== "__main__":
     main()