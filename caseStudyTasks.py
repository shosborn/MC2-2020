import random
from constants import Constants
import math
import sys
import csv
import time
#from gurobipy import *

wcet_map = {
'SD-VBS':{
   'texture_synt': 3.500985 ,
    'mser': 4.576398999999999 ,
    'tracking': 6.142087999999999 ,
    'disparity': 12.30912 ,
    'localization': 21.962538 ,
    'stitch': 22.805571999999998 ,
    'svm': 25.137069999999998 ,
    'sift': 36.1697 ,
    'multi_ncut': 4861.814272
    },
'DIS': {
   'neighborhood': 98.87772799999999,
   'field': 368.512,
   'matrix': 895.50112,
   'update': 921.9066879999999,
   'pointer': 1219.6355839999999,
   'transitive': 1251.7841919999998
},
'TACLe': {
   'petrinet': 0.003702,
   'statemate': 0.037925,
   'cjpeg_wrbm': 0.042533999999999995,
   'ndes': 0.044979,
   'fmref': 0.052031999999999995,
   'h264_dec': 0.07710499999999999,
   'huff_dec': 0.07955,
   'adpcm_dec': 0.08374,
   'adpcm_enc': 0.08520699999999999,
   'g723_enc': 0.09987399999999999,
   'huff_enc': 0.105391,
   'audiobeam': 0.11251499999999999,
   'gsm_dec': 0.165595,
   'cjpeg_tran': 0.181169,
   'epic': 0.22516899999999998,
   'rijndael_e': 0.240814,
   'rijndael_d': 0.24975399999999998,
   'anagram': 0.25589999999999996,
   'gsm_enc': 0.31554499999999996,
   'susan': 1.904305,
   'dijkstra': 3.819016,
   'ammunition': 8.924935999999999,
   'mpeg2': 11.445241
    }
}

acet_map = {
'SD-VBS':{
    'texture_synt': 3.2601419999999997 ,
    'mser': 4.316075 ,
    'tracking': 5.201947 ,
    'disparity': 11.753719 ,
    'stitch': 17.282014 ,
    'localization': 20.316338 ,
    'svm': 24.342458999999998 ,
    'sift': 34.437774 ,
    'multi_ncut': 4860.693216
    },
'DIS': {
   'neighborhood': 95.04602799999999,
   'field': 366.58606499999996,
   'matrix': 628.577951,
   'update': 916.460487,
   'transitive': 1032.6602269999998,
   'pointer': 1207.138986
    },
'TACLe': {
   'petrinet': 0.002012,
   'statemate': 0.006965,
   'ndes': 0.015097,
   'huff_dec': 0.019037,
   'cjpeg_wrbm': 0.020166,
   'h264_dec': 0.020307,
   'fmref': 0.028489,
   'adpcm_dec': 0.034856,
   'adpcm_enc': 0.035722,
   'g723_enc': 0.039626,
   'audiobeam': 0.040182999999999996,
   'huff_enc': 0.054422,
   'gsm_dec': 0.11111,
   'cjpeg_tran': 0.128642,
   'epic': 0.17216299999999998,
   'rijndael_e': 0.19980499999999998,
   'anagram': 0.20346499999999998,
   'rijndael_d': 0.207398,
   'gsm_enc': 0.272698,
   'susan': 1.711844,
   'dijkstra': 3.7653179999999997,
   'ammunition': 8.770932,
   'mpeg2': 11.36022
}
}

candidate_tasks = {'SD-VBS': {}, 'DIS':{}, 'TACLe': {}}

candidate_tasks['TACLe'] = {
    Constants.LEVEL_A: [ 'h264_dec', 'adpcm_enc', 'g723_enc', 'huff_enc', 'audiobeam', 'gsm_dec', 'cjpeg_tran', 'epic', 'rijndael_e', 'rijndael_d', 'anagram', 'gsm_enc'],
    #Constants.LEVEL_B: [ 'epic', 'rijndael_e', 'rijndael_d', 'anagram', 'gsm_enc'],
    #Constants.LEVEL_B: [ 'susan', 'dijkstra', 'ammunition'],
    Constants.LEVEL_B: ['h264_dec', 'huff_dec', 'adpcm_dec', 'adpcm_enc', 'g723_enc', 'huff_enc', 'audiobeam', 'gsm_dec', 'cjpeg_tran', 'epic', 'rijndael_e', 'rijndael_d', 'anagram', 'gsm_enc', 'susan', 'dijkstra'],
    Constants.LEVEL_C:['adpcm_dec', 'adpcm_enc', 'cjpeg_tran', 'cjpeg_wrbm', 'epic', 'fmref', 'gsm_dec', 'gsm_enc', 'h264_dec', 'huff_enc', 'rijndael_d', 'rijndael_e']
}

candidate_tasks['SD-VBS'] = {
    Constants.LEVEL_A: ['tracking', 'disparity', 'localization', 'svm'],
    Constants.LEVEL_B: ['disparity', 'localization', 'sift', 'stitch', 'svm'],
    Constants.LEVEL_C: ['disparity','localization','sift','svm','stitch','tracking','mser','texture_synt'],
}

candidate_tasks['DIS'] = {
    Constants.LEVEL_A: ['neighborhood', 'field'],
    Constants.LEVEL_B: ['field', 'matrix', 'pointer', 'transitive','update'],
    Constants.LEVEL_C: ['neighborhood', 'pointer', 'transitive', 'update'],
}


class Task:
    def __init__(self, name, level, cost, period = None, util= None):
        self.id = None
        self.name = name
        self.level = level
        self.cost = cost
        self.util = util
        self.period = period
        self.num_tasks = 0

def assign_program_to_levels(crit_util_dist,task_util_dist, dataset):
    for level in range(Constants.LEVEL_A, Constants.LEVEL_B+1):
        max_size_so_far = 0
        max_list = []
        for task in wcet_map[dataset]:
            list = [task]
            for task2 in wcet_map[dataset]:
                if wcet_map[dataset][task2] > wcet_map[dataset][task] and wcet_map[dataset][task2] < \
                        (Constants.TASK_UTIL[task_util_dist][level][1]/Constants.TASK_UTIL[task_util_dist][level][0])*wcet_map[dataset][task]:
                    list.append(task2)
            if len(list) > max_size_so_far and (level == Constants.LEVEL_A or (level==Constants.LEVEL_B and list!=candidate_tasks[dataset][Constants.LEVEL_A])):
                max_size_so_far = len(list)
                max_list = list
        candidate_tasks[dataset][level] = max_list
        #print(candidate_tasks[dataset][level])

def gen_task(core_count, target_util, crit_util_dist, task_util_dist, dataset):
    U_level = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    U_level_lb = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    U_level_ub = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    num_tasks = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    num_tasks_lb = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    num_tasks_ub = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    tasks = {Constants.LEVEL_A: [], Constants.LEVEL_B: [], Constants.LEVEL_C: []}
    periods = {Constants.LEVEL_A: [], Constants.LEVEL_B: [], Constants.LEVEL_C: []}
    #period_dist = {Constants.LEVEL_A: [1, 2, 4], Constants.LEVEL_B: [4, 8, 16], Constants.LEVEL_C: [2, 50]}
    period_dist = {Constants.LEVEL_A: [1, 2], Constants.LEVEL_B: [2, 4], Constants.LEVEL_C: [10, 100]}

    for level in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
        U_level_lb[level] = Constants.CRITICALITY_UTIL_DIST[crit_util_dist][level][0] * target_util
        U_level_ub[level] = Constants.CRITICALITY_UTIL_DIST[crit_util_dist][level][1] * target_util
        num_tasks_lb[level] = U_level_lb[level] / Constants.TASK_UTIL[task_util_dist][level][1]
        num_tasks_ub[level] = U_level_ub[level] / Constants.TASK_UTIL[task_util_dist][level][0]
        num_tasks[level] = random.randint(math.ceil(num_tasks_lb[level]), math.floor(num_tasks_ub[level]))
        for i in range(0, num_tasks[level]):
            tasks[level].append(candidate_tasks[dataset[level]][level][i % len(candidate_tasks[dataset[level]][level])])
            # periods[level].append(random.choice(period_dist[level]))
            if level == Constants.LEVEL_A:
                periods[level].append(1)
            else:
                periods[level].append(random.choice(period_dist[level]))
    for level in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
        sum = 0
        for level2 in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
            if level != level2:
                sum += U_level_lb[level2]
        U_level_ub[level] = min(U_level_ub[level], target_util - sum)

    '''print(U_level_lb, U_level_ub, num_tasks_lb, num_tasks_ub, num_tasks)
    print(tasks[Constants.LEVEL_A])
    print(tasks[Constants.LEVEL_B])
    print(tasks[Constants.LEVEL_C])
    print(periods)'''

    cost_l = 0
    cost_u = 0
    '''cost = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    for i in range(len(tasks[Constants.LEVEL_C])):
        cost_u += cost_map[dataset[level]][tasks[Constants.LEVEL_C][i]] / period_dist[Constants.LEVEL_C][0]
        cost_l += cost_map[dataset[level]][tasks[Constants.LEVEL_C][i]] / period_dist[Constants.LEVEL_C][1]'''

    x_max = 1000000000
    x_min = 0

    # assign_program_to_levels()
    #print(candidate_tasks)
    smallest_cost = {Constants.LEVEL_A: 1000000, Constants.LEVEL_B: 1000000, Constants.LEVEL_C: 1000000}
    highest_cost = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    for level in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
        for task in candidate_tasks[dataset[level]][level]:
            smallest_cost[level] = min(smallest_cost[level], wcet_map[dataset[level]][task])
            highest_cost[level] = max(highest_cost[level], wcet_map[dataset[level]][task])
            #cost[level] += cost_map[dataset[level]][task]

    for level in range(Constants.LEVEL_A, Constants.LEVEL_C + 1):
        max_util = Constants.TASK_UTIL[task_util_dist][level][1]
        min_util = Constants.TASK_UTIL[task_util_dist][level][0]
        x_min = max(x_min, highest_cost[level] / (period_dist[level][-1] * max_util))
        x_max = min(x_max, smallest_cost[level] / (period_dist[level][0] * min_util))
        #print("x_min: ", x_min, ", x_max: ", x_max)
        assert x_min <= x_max

    U = {Constants.LEVEL_A: 0, Constants.LEVEL_B: 0, Constants.LEVEL_C: 0}
    while True:
        U[Constants.LEVEL_A] = random.uniform(U_level_lb[Constants.LEVEL_A], U_level_ub[Constants.LEVEL_A])
        U[Constants.LEVEL_B] = random.uniform(U_level_lb[Constants.LEVEL_B], U_level_ub[Constants.LEVEL_B])
        U[Constants.LEVEL_C] = target_util - U[Constants.LEVEL_A] - U[Constants.LEVEL_B]
        if U[Constants.LEVEL_C] <= U_level_ub[Constants.LEVEL_C] and U[Constants.LEVEL_C] >= U_level_lb[
            Constants.LEVEL_C]:
            break
    tot_U = U[Constants.LEVEL_C]+U[Constants.LEVEL_A]+U[Constants.LEVEL_B]
    #print(U, tot_U)
    x = 48#random.randint(math.ceil(x_min), math.floor(x_max))
    assert x <= math.floor(x_max) and x>= math.ceil(x_min)
    task_set = {Constants.LEVEL_A: [], Constants.LEVEL_B: [], Constants.LEVEL_C: []}
    tot_util = 0
    for level in range(Constants.LEVEL_A, Constants.LEVEL_B + 1):
        u = 0
        for task in candidate_tasks[dataset[level]][level]:
            for period in period_dist[level]:
                util = wcet_map[dataset[level]][task] / (period * x)
                if util <= Constants.TASK_UTIL[task_util_dist][level][1] and util >= \
                        Constants.TASK_UTIL[task_util_dist][level][0]:
                    t = Task(name=task, cost=wcet_map[dataset[level]][task], period=period * x, util=util, level=level)
                    if u + util <= U[level]:
                        t.num_tasks = 1
                        task_set[level].append(t)
                        u += util
        '''_u = 0
        for task in task_set[level]:
            _u += task.num_tasks * cost_map[dataset[level]][task.name] / (task.period)
        assert u == _u'''
        task_count = len(task_set[level])
        while u <= U[level]:
            index = random.randint(0, task_count - 1)
            assert task_set[level][index].util == wcet_map[dataset[level]][task_set[level][index].name] / task_set[level][index].period
            if u + task_set[level][index].util > U[level]:
                #print(u)
                break
            u += task_set[level][index].util
            task_set[level][index].num_tasks += 1
        '''_u = 0
        for task in task_set[level]:
            _u += task.num_tasks * cost_map[dataset[level]][task.name] / (task.period)

        assert u == _u'''
        U[Constants.LEVEL_C] += (U[level] - u)
        tot_util += u


    u = 0

    for task in candidate_tasks[dataset[Constants.LEVEL_C]][Constants.LEVEL_C]:
        period_min = wcet_map[dataset[Constants.LEVEL_C]][task] / Constants.TASK_UTIL[task_util_dist][Constants.LEVEL_C][1]
        period_max = wcet_map[dataset[Constants.LEVEL_C]][task] / Constants.TASK_UTIL[task_util_dist][Constants.LEVEL_C][0]
        period_min = max(x * period_dist[Constants.LEVEL_C][0], period_min)
        period_max = min(x * period_dist[Constants.LEVEL_C][-1], period_max)
        if period_min <= period_max:
            period = random.randint(math.ceil(period_min), math.floor(period_max))
            util = wcet_map[dataset[Constants.LEVEL_C]][task] / period
            if u + util <= U[Constants.LEVEL_C]:
                task_set[Constants.LEVEL_C].append(
                    Task(name=task, level=Constants.LEVEL_C, period=[period], util=None, cost=wcet_map[dataset[Constants.LEVEL_C]][task]))
                u += util

    task_count = len(task_set[Constants.LEVEL_C])
    while u <= U[Constants.LEVEL_C]:
        index = random.randint(0, task_count - 1)
        task = task_set[Constants.LEVEL_C][index].name
        period_min = wcet_map[dataset[Constants.LEVEL_C]][task] / Constants.TASK_UTIL[task_util_dist][Constants.LEVEL_C][1]
        period_max = wcet_map[dataset[Constants.LEVEL_C]][task] / Constants.TASK_UTIL[task_util_dist][Constants.LEVEL_C][0]
        period_min = max(x * period_dist[Constants.LEVEL_C][0], period_min)
        period_max = min(x * period_dist[Constants.LEVEL_C][-1], period_max)
        if period_min <= period_max:
            period = random.randint(math.ceil(period_min), math.floor(period_max))
            util = wcet_map[dataset[Constants.LEVEL_C]][task] / period
            if u + util <= U[Constants.LEVEL_C]:
                task_set[Constants.LEVEL_C][index].period.append(period)
                # task_set[Constants.LEVEL_C].append(
                #    Task(name=task, level=Constants.LEVEL_C, period=[period], util=None, cost=cost_map[task]))
                u += util
            else:
                #print(u)
                break
    tot_util += u
    #print("total util: ", tot_util)
    c= 0
    with open('temp_task_set.csv', "w", newline='\n', encoding='utf-8') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['task id', 'suite', 'benchmark', 'crit level', 'level-A pet(us)', 'period (ms)', 'wss'])
        for level in range(Constants.LEVEL_A, Constants.LEVEL_B + 1):
            for task in task_set[level]:
                for i in range(task.num_tasks):
                    csvwriter.writerow(
                        [c,dataset[level], task.name,task.level,task.cost*1000,task.period,2])#acet_map[dataset[level]][task.name],task.num_tasks
                    c += 1
        for task in task_set[Constants.LEVEL_C]:
            for period in task.period:
                csvwriter.writerow(
                    [c,dataset[Constants.LEVEL_C],task.name,task.level,task.cost*1000,period,2])
                c+=1
    '''for level in range(Constants.LEVEL_A, Constants.LEVEL_B + 1):
        for task in task_set[level]:
            print(task.level,",",task.name,",",task.period,",",task.cost,",",task.num_tasks)

    for task in task_set[Constants.LEVEL_C]:
        for period in task.period:
            print(task.level,",",task.name,",",period,",",task.cost,",",1)'''

def readwcet(filename):
    header = False
    name = []
    map = {'acet': {}, 'wcet': {}}
    with open(filename, "r") as f:
        for line in f:
            arr = line.split(",")
            if header:
                for i in range(1,len(arr)):
                    name.append(arr[i])
                    #map[arr[i]] = {}
                header = False
            else:
                task1 = arr[0]
                map['acet'][task1] = float(arr[1])*1e-6
                map['wcet'][task1] = float(arr[2])*1e-6

    for cost in ['acet','wcet']:
        map[cost] = {k: v for k, v in sorted(map[cost].items(), key=lambda item: item[1])}
        print(cost)
        print()
        for task in map[cost]:
            print('\'',task,'\':',map[cost][task],",")
        print()

def readMij(filename):
    header = True
    name = []
    map = {}
    with open(filename, "r") as f:
        for line in f:
            low_tri = True
            arr = line.split(",")
            if header:
                for i in range(1,len(arr)):
                    name.append(arr[i])
                    #map[arr[i]] = {}
                header = False
            else:
                task1 = arr[0]
                map[task1] = {}
                for i in range(1,len(arr)):
                    if task1 == name[i-1].strip():
                        low_tri = False
                    if not low_tri:
                        map[task1][name[i - 1].strip()] = float(arr[i]) if arr[i].find('N/A')<0 else 60
                    else:
                        map[task1][name[i - 1].strip()] = map[name[i-1].strip()][task1]

    #print(map)

def convert_to_ms():
    for benchmark in ['DIS', 'TACLe']:
        for task in wcet_map[benchmark]:
            wcet_map[benchmark][task] *= 1e-6  # convert to ns to ms
            #print(task,cost_map[benchmark][task])

def inflate():
    for benchmark in ['DIS', 'TACLe','SD-VBS']:
        for task in wcet_map[benchmark]:
            wcet_map[benchmark][task] *= 1.5


def main():
    #random.seed(12345)
    core_count = 8
    target_util = 8
    #crit_util_dist = 'C-Heavy'
    crit_util_dist = 'AB-Moderate'
    task_util_dist = 'Moderate_Util'
    #readMij('DIS_mij.csv')
    #readwcet('SDVBS_wcet.csv')
    #convert_to_ms()
    inflate()
    benchmark = {Constants.LEVEL_A: 'TACLe', Constants.LEVEL_B: 'TACLe', Constants.LEVEL_C: 'SD-VBS'}
    #assign_program_to_levels(crit_util_dist,task_util_dist,'TACLe')
    gen_task(core_count,target_util,crit_util_dist,task_util_dist,benchmark)

if __name__ == "__main__":
    main()
