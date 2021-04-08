# Schedulability Test and Taskset Generation Code for the MC² Project
This code only supports modeling MC² systems with SMT. This has been developed by the Real-Time Systems group in the Computer Science Department at UNC Chapel Hill. All code is GPL-3 licenced unless otherwise stated.

## Dependecies
1. Python 3.6 or higher
2. Gurobi with Python bindings
3. NumPy
4. Matplotlib (for graphing)

Gurobi is commercial software, however free academic licences are available. Please follow [these instructions](https://www.gurobi.com/academia/academic-program-and-licenses/) to obtain Gurobi and add it to your PATH. Please see your package maintainers on how to obtain a recent version of Python if your current version is too old. We do not support running on Windows.

On Ubuntu 20.04, the other dependencies can be obtained via `sudo apt install python3-numpy python3-matplotlib`.

## Running Schedulability Studies
To run the schedulability study experiments, create a folder named 'results' and execute the following:
``` shell
python sched_study.py -m <number of cores> -c <cores per core-complex> -p <period> -s <SMT effectiveness> -u <per-task utilization> -r <criticality distrbution>
                      -l <maximum threaded util> -t <track spent time> -v <verbose> -d <debug> 
```
where<br />
`<period>` should be one of `{'Long', 'Short', 'Many','Contrasting'}`,<br />
`<SMT effectiveness>` should be one of `{'DIS_SMTv2','TACLE_SMTv2','SDVBS_SMTv2','Prior_SMTv2','TACLE_v_SDVBS_SMTv2'}`,<br />
`<per-task utilization>` should be one of `{'Heavy_Util','Moderate_Util','Light_Util'}`,<br />
`<criticality distrbution>` should be one of `{'AB-Moderate','C-Heavy'}`,<br />
`<maximum threaded util>` should be a number between 0 and 1.<br />
See the paper for detail about the parameter choices.

Example:
``` shell
./sched_study.py -m 8 -p Long -r AB-Moderate -u Light_Util -s TACLE_v_SDVBS_SMTv2
```

To create schedulibity plots, create a folder named 'plots' and two folders named 'pdfs' and 'pngs' underneath it, and then execute `./schedplot.py`.

To generate SUAs execute `./aggregator.py`.

## Schedulability test for case study tasks
There are 10 task sets schedulable with SMT in the directory `case_study_tasks` corresponding to the highest schedulable utilization (5.5) for scenario  `AB-Moderate, Long, Light_Util, TACLe_SDVBS_SMTv2` on 8 processors. To test the schedulability, execute the following.
``` shell
python case_study_run.py -m <number of cores> -u <system utilization> -A <Level-A task benchmark> -B <Level-B task benchmark> -C <Level-C task benchmark> -f <task set filepath>
```
where <br />
`<system utilization>` is task set's total utilization at Level-A (the point on x-axis in schedulability plot for which the corresponding task set is generated),<br />
`<Level-A task benchmark>` is benchmarks for Level-A tasks (default `TACLe`), <br />
`<Level-B task benchmark>` is benchmarks for Level-B tasks (default `TACLe`), <br />
`<Level-C task benchmark>` is benchmarks for Level-C tasks (default `SD-VBS`), <br />
`<file path>` is path to the input file (`all_tasks.csv` files under folder `case_study_tasks/<ID>/`). <br />
If the task set is schedulable, three files will be generated in the folder containing the input task sets. The generated files `l3alloc.csv, levelAB_pairs.csv, levelC_threads.csv` contain L3 allocation decisions, Level-A and -B task pairing decisions, and Level-C threading decisions, respectively.<br />

Example:
``` shell
python case_study_run.py -m 8 -u 5.5 -A TACLe -B TACLe -C SD-VBS -f case_study_tasks/1/all_tasks.csv
```

## Case study task generation
Schedulable task sets can be generated for `TACLe_SDVBS_SMTv2` SMT-effectiveness, `Light` per-task utilizations, and `Long` period distribution. To generate a task set, execute the following.
``` shell
python case_study_task_gen.py -m <number of cores> -u <system utilization> -r <criticality distribution> -n <task set ID>
```
The task set will be stored in `case_study_tasks/<task set ID>` folder. The files `all_tasks.csv, l3alloc.csv, levelAB_pairs.csv, levelC_threads.csv` contain parameters of all tasks, L3 allocation decisions, Level-A and -B task pairing decisions, and Level-C threading decisions, respectively.

Example:
``` shell
python case_study_task_gen.py -m 8 -u 5.5 -r AB-Moderate -n 1
```
Task generation can take time depending on the scenario and target system utilization.
