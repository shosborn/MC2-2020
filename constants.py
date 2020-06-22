class Constants:
    # system-wide constants
    LEVEL_A = 0
    LEVEL_B = 1
    LEVEL_C = 2

    # positions in allCosts key
    SIBLING = 0
    CRIT_LEVEL = 1
    CACHE_PORTIONS = 2

    WORST_FIT = 0
    PERIOD_AWARE_WORST = 1

    ASSUMED_MAX_CAPACITY = 1

    # maximum threaded util
    '''
    observation: making this 1 makes systems less schedulable,
    despite 1 being the best choice to minimize total util
    Best choice is dependent on the number of threads/ cluster?
    '''
    MAX_THREADED_UTIL = .7

    #related to overheads
    #column header from overhead data file
    '''
    overheadTypes = {'CXS': 'contextSwitch',
                     'ISR': 'interruptService',
                     'SCH': 'schedA',
                     'SCL': 'schedC',
                     'RLA': 'releaseLatencyA',
                     'RLC': 'releaseLatencyC',
                     'RQA': 'release',
                     'RQC': 'releaseC',
                     'TCK': 'tick',
                     'SCHED': 'sched',
                     'SCHED2': 'sched2',
                     'SRD': 'SRD',
                     'RLY': 'release_latency'
                     }
    '''

    OVERHEAD_TYPES = {
                     'releaseLatency':'RLA', #delay until ISR starts execution
                     'ipiLatency':'IPI', #delay until ipi is received
                     'scheduling':'SCH', #process selection
                     'contextSwitch':'CXS', #process switch
                     'release':'RQA', #execution of release ISR
                     'tick':'TCK', #execution of timer tick ISR
                     #'smtOverhead':'SMT'
                     }

    QUANTUM_LENGTH = 1000

    CPMD_PER_UNIT = [0, 10, 8] #constant b^l from miccaiah et al RTSS'15, 0 for level-A (no CPMD for cyclic executive)

    CPI_PER_UNIT = [0, 0, 0]#assumed to be small

    SMT_OVERHEAD = 1 #assuming SMT overhead as constant, need to determine whether it depends on number of tasks

    IS_DEDICATED_IRQ = False

    OVERHEAD_ACCOUNT = True

    #related to sched study params

    CORES_PER_COMPLEX = 4
    NUM_CORES = 4
    UTIL_STEP_SIZE = 1

    CACHE_LEVELS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 
                    10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 
                    20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                    30, 31, 32)

    # use for debugging
    # CACHE_LEVELS=(0, 1, 2)
    
    # size of one L3 cache way, in MB
    WAY_SIZE = 1

    MAX_SAMPLES = 2 #set at 2 for intial testing

    LIGHT_RATIO = (0.1, 0.3)
    LOW_MODERATE_RATIO = (0.2, 0.3)
    HIGH_MODERATE_RATIO = (0.35, 0.45)
    HEAVY_RATIO = (0.4, 0.6)
    #HEAVY_RATIO = (0.5, 0.7)

    #change based on data from Josh
    CRIT_SENSITIVITY = 2   
    

    # for all of the following, abreviated versions with the same name may be useful for debugging.

    # from RTSS '15
    CRITICALITY_UTIL_DIST = {
       'C-Heavy':      [LIGHT_RATIO, LIGHT_RATIO],
       'B-Heavy':      [LOW_MODERATE_RATIO, HEAVY_RATIO],
       'AB-Moderate':  [HIGH_MODERATE_RATIO, HIGH_MODERATE_RATIO],
    }


    # from RTSS '15
    PERIOD_DIST = { #in ms (need to be in us?)
        'Short':        [(3, 6), (6, 12), (3, 33)],
        'Contrasting':  [(3, 6), (96, 192), (10, 100)],
        'Long':         [(48, 96), (96, 192), (50, 500)]
    }

    # from RTSS '15
    TASK_UTIL = {
        'Light_Util':    [(0.001, 0.03), (0.001, 0.05), (0.001, 0.1)],
        'Moderate_Util': [(0.02, 0.1), (0.05, 0.2), (0.1, 0.4)],
        'Heavy_Util':    [(0.1, 0.2), (0.2, 0.4), (0.4, 0.6)]
    }
    
    # Joshua's Numbers
    CACHE_SENSITIVITY = {
         'Default_Sensitivity':   [2, 8, 16]
    }
    
    # Joshua's suggestion--units are MB
    # Normal distribution
    # truncate negative values
    WSS_DIST = {
        'Default_WSS': [2.0, 2.0]
    }
    
    # first element is for levels A and B (from ECRTS '20)
    # second is for Level C (from ECRTS '19, kind of)
    SMT_EFFECTIVENESS_DIST = {
    'High':     [(.45, .12, 0.0), (.45, .12, 0.0), (1.1, .1)],
    'Moderate': [(.45, .12, 0.2), (.45, .12, 0.2), (1.45, .1)],
    'Low':      [(.6, .07, .2), (.6, .07, .2), (1.8, .1)]  
    }

    
    
    
    
    
    '''
    # Shareef's version
    CRITICALITY_UTIL_DIST = {
        'A-Heavy':      [HEAVY_RATIO, LIGHT_RATIO, LIGHT_RATIO],
        'B-Heavy':      [LIGHT_RATIO, HEAVY_RATIO, LIGHT_RATIO],
        'C-Heavy':      [LIGHT_RATIO, LIGHT_RATIO, HEAVY_RATIO],
        'AB-Moderate':  [MODERATE_RATIO, MODERATE_RATIO, LIGHT_RATIO],
        'AC-Moderate':  [MODERATE_RATIO, LIGHT_RATIO, MODERATE_RATIO],
        'BC-Moderate':  [LIGHT_RATIO, MODERATE_RATIO, MODERATE_RATIO],
        'ALL-Moderate': [MODERATE_RATIO, MODERATE_RATIO, MODERATE_RATIO],
    }
'''


