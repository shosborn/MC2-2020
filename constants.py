class Constants:
    # system-wide constants
    LEVEL_A = 0
    LEVEL_B = 1
    LEVEL_C = 2


    # positions in allCosts key
    SIBLING = 0
    CRIT_LEVEL = 1
    CACHE_PORTIONS=2

    WORST_FIT = 0
    PERIOD_AWARE_WORST = 1

    ASSUMED_MAX_CAPACITY = 1

    #column header from overhead data file
    overheadTypes = {'CXS': 'CXS',
                     'ISR': 'ISR',
                     'SCH': 'SCHED_A',
                     'SCL': 'SCHED_C',
                     'RLA': 'RELEASE_LATENCY_A',
                     'RLC': 'RELEASE_LATENCY_C',
                     'RQA': 'RELEASE',
                     'RQC': 'RELEASE_C',
                     'TCK': 'TICK',
                     'SCHED': 'SCHED',
                     'SCHED2': 'SCHED2',
                     'SRD': 'SRD',
                     'RLY': 'RELEASE_LATENCY'
                     }