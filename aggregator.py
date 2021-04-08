#!/usr/bin/env python3
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
              'MAX_THREADED_UTIL',
              'CORE_COUNT']
schemes = ['SOLO',
           'THREADED']

def aggregate():
    res_files = os.listdir(results_path)
    writer = csv.DictWriter(open('aggregate.csv','w'),parameters + schemes)
    suas = {scheme: [] for scheme in schemes}
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
        # Compute areas by trapezoid rule
        for util in scenario_data['SOLO'].keys():
            for scheme in schemes:
                if util == max_util or util == min_util:
                    write_row[scheme] += 0.5*scenario_data[scheme][util]
                else:
                    write_row[scheme] += scenario_data[scheme][util]
        for scheme in schemes:
            suas[scheme].append(write_row[scheme])
        writer.writerow(write_row)
    # Note that we compute the % improvement in average SUAs, NOT the average %
    # improvement in SUAs. This calculation approach avoids overweighting
    # scenarios where the SUA changes very little in absolute terms, but a lot
    # in percentage terms (such as where SUA goes from 0.01 to 0.05).
    last_scheme = ""
    last_avg_sua = 0
    for scheme in schemes:
        our_avg_sua = sum(suas[scheme])/len(suas[scheme])
        print("Average", scheme, "SUA:", our_avg_sua)
        if last_avg_sua != 0:
            print("Average", scheme, "SUA is a", (our_avg_sua - last_avg_sua) / last_avg_sua * 100, "percent improvement over average", last_scheme, "SUA");
        last_avg_sua = our_avg_sua
        last_scheme = scheme

if __name__ == "__main__":
    aggregate()
