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
    
    # maximum threaded util
    '''
    observation: making this 1 makes systems less schedulable,
    despite 1 being the best choice to minimize total util
    Best choice is dependent on the number of threads/ cluster?
    '''
    MAX_THREADED_UTIL = .7