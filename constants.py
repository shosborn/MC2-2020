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

    CPMD_PER_UNIT = [0, 10, 8] #constant b^l from miccaiah et al RTSS'15, 0 for level-A (no CPMD for cyclic executive)

    CPI_PER_UNIT = [0, 0, 0]#assumed to be small

    SMT_OVERHEAD = [3,2,1] #assuming SMT overhead as constant, need to determine whether it depends on number of tasks

    IS_DEDICATED_IRQ = True

    OVERHEAD_ACCOUNT = True

    #related to sched study params

    CORES_PER_COMPLEX = 4
    NUM_CORES = 16
    UTIL_STEP_SIZE = 0.2

    MAX_HALF_WAYS = 16

    MAX_SAMPLES = 2 #set at 2 for intial testing

    LIGHT_RATIO = (0.1, 0.3)
    MODERATE_RATIO = (0.1, 0.3)
    HEAVY_RATIO = (0.5, 0.7)

    CRITICALITY_UTIL_DIST = {
        'A-Heavy':      [HEAVY_RATIO, LIGHT_RATIO, LIGHT_RATIO],
        'B-Heavy':      [LIGHT_RATIO, HEAVY_RATIO, LIGHT_RATIO],
        'C-Heavy':      [LIGHT_RATIO, LIGHT_RATIO, HEAVY_RATIO],
        'AB-Moderate':  [MODERATE_RATIO, MODERATE_RATIO, LIGHT_RATIO],
        'AC-Moderate':  [MODERATE_RATIO, LIGHT_RATIO, MODERATE_RATIO],
        'BC-Moderate':  [LIGHT_RATIO, MODERATE_RATIO, MODERATE_RATIO],
        'ALL-Moderate': [MODERATE_RATIO, MODERATE_RATIO, MODERATE_RATIO],
    }

    PERIOD_DIST = { #in ms (need to be in us?)
        'Short':        [(3, 6), (6, 12), (3, 33)],
        'Contrasting':  [(3, 6), (96, 192), (10, 100)],
        'Long':         [(48, 96), (96, 192), (50, 500)]
    }

    TASK_UTIL = {
        'Light':    [(0.001, 0.03), (0.001, 0.05), (0.001, 0.1)],
        'Moderate': [(0.02, 0.1), (0.05, 0.2), (0.1, 0.4)],
        'Heavy':    [(0.1, 0.2), (0.2, 0.4), (0.4, 0.6)]
    }

    DEBUG = False

