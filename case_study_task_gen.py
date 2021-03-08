from singleRun import main
from caseStudyTasks import gen_task,convert_to_ms,wcet_map,inflate
from constants import Constants
import argparse

def run():
    #convert_to_ms()
    parser = argparse.ArgumentParser()
    # parser.add_argument('-d', "--datafile", type = argparse.FileType('w'),
    # default = sys.stdout,
    # help = "File to output csv file to")
    parser.add_argument('-m', "--processors", default=Constants.NUM_CORES, type=int, help="Number of cores")
    parser.add_argument('-u', "--sysUtil", default=Constants.NUM_CORES, type=float, help="System utilization")
    parser.add_argument('-c', "--corePerComplex", default=Constants.CORES_PER_COMPLEX, type=int,
                        help="Number of cores per complex")
    parser.add_argument('-p', "--period", default="Long", help="Period distribution")
    #parser.add_argument('-s', "--smt", default="All", help="SMT effectiveness")
    parser.add_argument('-a', "--util", default="Light_Util", help="per-task util")
    parser.add_argument('-r', "--crit", default="AB-Moderate", help="criticality util")
    parser.add_argument('-l', "--limitThreadUtil", default=Constants.MAX_THREADED_UTIL, type=float,
                        help="Max threaded util")
    parser.add_argument('-A', "--levelA", default="TACLe", help="level-A benchmark")
    parser.add_argument('-B', "--levelB", default="TACLe", help="level-B benchmark")
    parser.add_argument('-C', "--levelC", default="SD-VBS", help="level-C benchmark")
    parser.add_argument('-n', "--taskSetID", default="1", help="task set id")

    args = parser.parse_args()
    core_count = args.processors
    target_util = args.sysUtil
    crit_util_dist = args.crit # 'AB-Moderate'
    task_util_dist = args.util # 'Light_Util'
    benchmark = {Constants.LEVEL_A: 'TACLe', Constants.LEVEL_B: 'TACLe', Constants.LEVEL_C: 'SD-VBS'}
    i = int(args.taskSetID)
    success = False
    inflate()
    while not success:
        #print("iteraton: ",i)
        #crit_util_dist = 'C-Heavy'
        #task_util_dist = 'Moderate_Util'
        # assign_program_to_levels(crit_util_dist,task_util_dist,'TACLe')
        gen_task(core_count, target_util, crit_util_dist, task_util_dist, benchmark)
        if main(target_util,benchmark,i):
            success = True
            break
    #print(success)

if __name__ == '__main__':
    run()