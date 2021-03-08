# MC2-2020
Support for schedulability tests incorporating SMT in the MC-Squared project (UNC-CH, Dept. Comp. Sci., Real-Time)

## Dependecies
1. python 3.6 or higher
2. Gurobi

## Running Schedulability Studies
To run the schedulability study experiments, create a folder named 'Results' and execute the following:
``` shell
python sched_study.py -m <number of processors> -c <cores per core-complex> -p <period> -s <SMT effectiveness> -u <per-task utilization> -r <criticality distrbution>
                      -l <maximum threaded util> -t <track spent time> -v <verbose> -d <debug> 
```
where
`<period>` should be one of `{'Long', 'Short', 'Many','Contrasting'}`,
`<SMT effectiveness>` should be one of `{'DIS_SMTv2','TACLE_SMTv2','SDVBS_SMTv2','Prior_SMTv2','TACLE_v_SDVBS_SMTv2'}`,
`<per-task utilization>` should be one of `{'Heavy_Util','Moderate_Util','Light_Util'}`,
`<criticality distrbution>` should be one of `{'AB-Moderate','C-Heavy'}`
`<maximum threaded util>` should be a number between 0 and 1.
See the paper for detail about the parameter choices.

Example:
``` shell
python sched_study.py -m 8 -p Long -r AB-Moderate -u Light_Util -s TACLE_v_SDVBS_SMTv2
```

To create schedulibity plots, create a folder named 'plots' and two folders named 'pdfs' and 'pngs' underneath it, and execute the following
``` shell
python schedplot.py
```

To generate SUAs execute the following
``` shell
python aggregator.py
```
