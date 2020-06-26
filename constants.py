from typing import Dict, Tuple

class Constants:
    # system-wide constants
    LEVEL_A = 0
    LEVEL_B = 1
    LEVEL_C = 2
    MAX_LEVEL = 3

    # positions in allCosts key
    SIBLING = 0
    CRIT_LEVEL = 1
    CACHE_PORTIONS = 2

    WORST_FIT = 0
    PERIOD_AWARE_WORST = 1

    ASSUMED_MAX_CAPACITY = 1

    THREAD_PER_CORE = 2

    # maximum threaded util
    '''
    observation: making this 1 makes systems less schedulable,
    despite 1 being the best choice to minimize total util
    Best choice is dependent on the number of threads/ cluster?
    '''
    MAX_THREADED_UTIL = .7

    #related to cache allocation

    CORE_LEVEL_ISOLATION = 0 #two threads of a core share cache for level-A,-B tasks, option 2 from joshua
    THREAD_LEVEL_ISOLATION = 1 #two threads of a core gets isolated cache allocation for level-A,-B tasks, option 4 from joshua

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

    SIZE_OF_HALF_WAYS = 0.5 #1 half way = 0.5 MB

    CPMD_PER_UNIT: Dict[int, float] = {LEVEL_A: 0, LEVEL_B: 10, LEVEL_C: 8} #constant b^l from miccaiah et al RTSS'15, 0 for level-A (no CPMD for cyclic executive)

    CPI_PER_UNIT = [0, 0, 0]#assumed to be small

    SMT_OVERHEAD: Dict[int, float] = {LEVEL_A: 3, LEVEL_B: 2, LEVEL_C: 1} #assuming SMT overhead as constant, need to determine whether it depends on number of tasks

    IS_DEDICATED_IRQ = True

    OVERHEAD_ACCOUNT = True

    #related to sched study params

    CORES_PER_COMPLEX = 4
    NUM_CORES = 8
    UTIL_STEP_SIZE = 0.5

    CACHE_LEVELS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 
                    10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 
                    20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                    30, 31, 32)

    # use for debugging
    # CACHE_LEVELS=(0, 1, 2)
    #in MB
    CACHE_SIZE_L3 = 16

    # size of one L3 cache way, in MB
    WAY_SIZE = 1

    # It's technically possible for a solo task to occupy all ways
    MAX_HALF_WAYS = 32

    MIN_SAMPLES = 10
    MAX_SAMPLES = 25 #set at 2 for initial testing
    CONF_INTERVAL = 0.05
    CONF_LEVEL = 0.95

    #Schemes
    NO_THREAD = 0
    THREAD_COURSE = 1
    THREAD_FINE = 2

    LIGHT_RATIO = (0.1, 0.3)
    LOW_MODERATE_RATIO = (0.2, 0.3)
    HIGH_MODERATE_RATIO = (0.35, 0.45)
    #HEAVY_RATIO = (0.4, 0.6)
    HEAVY_RATIO = (0.5, 0.7)

    #I'm interpreting this as the fraction my Level \ell cost is relative to my Level A cost
    #normally distributed
    CRIT_SENSITIVITY: Dict[str, Dict[int,Tuple[float,float]]] = {
        'Default_Crit_Sensitivity': {LEVEL_A: (1.0, 0.0), LEVEL_B: (0.66, 0.1), LEVEL_C: (0.5, 0.1)}
    }
    

    # for all of the following, abreviated versions with the same name may be useful for debugging.

    # from RTSS '15
    CRITICALITY_UTIL_DIST: Dict[str, Dict[int,Tuple[float,float]]] = {
        'C-Heavy':      {LEVEL_A: LIGHT_RATIO, LEVEL_B: LIGHT_RATIO, LEVEL_C: HEAVY_RATIO},
        'C-All':      {LEVEL_A: (0.0, 0.0), LEVEL_B: (0.0,0.0), LEVEL_C: (1.0,1.0)},
        'C-None':       {LEVEL_A: (0.4,0.6), LEVEL_B: (0.4,0.6), LEVEL_C: (0.0,0.0)},
       #'B-Heavy':      {LEVEL_A: LOW_MODERATE_RATIO, LEVEL_B: HEAVY_RATIO, LEVEL_C: LIGHT_RATIO},
       'AB-Moderate':  {LEVEL_A: HIGH_MODERATE_RATIO, LEVEL_B: HIGH_MODERATE_RATIO, LEVEL_C: LIGHT_RATIO},
    }


    # from RTSS '15
    PERIOD_DIST: Dict[str, Dict[int,Tuple[int,int]]] = { #in ms, converted to us in Task generation
        'Short':        {LEVEL_A: (3, 6), LEVEL_B: (6, 12), LEVEL_C: (3, 33)},
        #'Contrasting':  {LEVEL_A: (3, 6), LEVEL_B: (96, 192), LEVEL_C: (10, 100)},
        'Long':         {LEVEL_A: (48, 96), LEVEL_B: (96, 192), LEVEL_C: (50, 500)}
    }

    # from RTSS '15
    TASK_UTIL: Dict[str, Dict[int,Tuple[float,float]]] = {
        #'Light_Util':    {LEVEL_A: (0.001, 0.03), LEVEL_B: (0.001, 0.05), LEVEL_C: (0.001, 0.1)},
        'Moderate_Util': {LEVEL_A: (0.02, 0.1), LEVEL_B: (0.05, 0.2), LEVEL_C: (0.1, 0.4)},
        #'Heavy_Util':    {LEVEL_A: (0.1, 0.2), LEVEL_B: (0.2, 0.4), LEVEL_C: (0.4, 0.6)}
    }
    
    # Informed by benchmarks
    CACHE_SENSITIVITY: Dict[str, Tuple[float,float,float]] = {
         'Default_Sensitivity':   (1.16, 2.95, 15.68)
    }
    
    # units are MB
    # Normal distribution
    # truncate negative values
    WSS_DIST: Dict[str, Tuple[float,float]] = {
        'Default_WSS': (2.0, 2.0)
    }
    
    # first element is for levels A and B (from ECRTS '20)
    # second is for Level C (from ECRTS '19, kind of)
    # level C contains an extra 0 for type consistency
    SMT_EFFECTIVENESS_DIST: Dict[str, Dict[int,Tuple[float,float,float]]] = {
        'High':     {LEVEL_A: (.45, .12, 0.0), LEVEL_B: (.45, .12, 0.0), LEVEL_C: (1.1, .1, 0)},
        #'Moderate': {LEVEL_A: (.45, .12, 0.2), LEVEL_B: (.45, .12, 0.2), LEVEL_C: (1.45, .1, 0)},
        'Low':      {LEVEL_A: (.6, .07, .2), LEVEL_B: (.6, .07, .2), LEVEL_C: (1.8, .1, 0)},
        'None':     {LEVEL_A: (2.0, 0.0, 1.0), LEVEL_B: (2.0, 0.0, 1.0), LEVEL_C: (3.0, 0.0, 0)}
    }

    
    
    
    
    
    '''
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


    DEBUG = False
    VERBOSE = False
    TIMEKEEPING = False
    RUN_FINE = True

