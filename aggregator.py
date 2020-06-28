
import csv
import os
from typing import Dict

results_path = "results/"
parameters = ['CRIT_UTIL_DIST',
              'PERIOD_DIST',
              'TASK_UTIL_DIST',
              'CACHE_SENSITIVITY',
              'WSS_DIST',
              'SMT_EFFECTIVENESS_DIST',
              'CRIT_SENSITIVITY',
              'MAX_THREADED_UTIL',
              'CORE_COUNT']
schemes = ['SOLO',
           'THREADED']

def aggregate():
    res_files = os.listdir(results_path)
    writer = csv.DictWriter(open('aggregate.csv','w'),parameters + schemes)
    for rf in res_files:
        file_parameters = rf.split("__")
        write_row = {}
        #indexes are scheme, sys_util : fraction schedulable
        scenario_data: Dict[str, Dict[float,float]] = {'SOLO':{}, 'THREADED': {}}
        for idx in range(len(parameters)):
            write_row[parameters[idx]] = file_parameters[idx]
        for scheme in schemes:
            write_row[scheme] = 0
        reader = csv.DictReader(open(results_path + rf,'r'))
        min_util = 1e10
        max_util = -1e10
        for row in reader:
            util = float(row["SYS_UTIL"])
            min_util = min([min_util, util])
            max_util = max([max_util, util])
            scenario_data['SOLO'][util] = float(row["NO_THREAD"])
            scenario_data['THREADED'][util] = float(row["THREAD_COURSE"])
        #Compute areas by trapezoid rule
        for util in scenario_data['SOLO'].keys():
            for scheme in schemes:
                if util == max_util or util == min_util:
                    write_row[scheme] += 0.5*scenario_data[scheme][util]
                else:
                    write_row[scheme] += scenario_data[scheme][util]
        writer.writerow(write_row)

if __name__ == "__main__":
    aggregate()