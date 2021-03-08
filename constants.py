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
                     'releaseLatency':'RELEASE-LATENCY', #delay until ISR starts execution
                     'ipiLatency':'SEND-RESCHED', #delay until ipi is received
                     'scheduling':'SCHED', #process selection
                     'contextSwitch':'CXS', #process switch
                     'release':'RELEASE', #execution of release ISR
                     'tick':'SCHED', #execution of timer tick ISR
                     }

    QUANTUM_LENGTH = 1000

    SIZE_OF_HALF_WAYS = 0.5 #1 half way = 0.5 MB

    CPMD_PER_UNIT: Dict[int, float] = {LEVEL_A: 0, LEVEL_B: 292, LEVEL_C: 238} # Microseconds. Constant b^l from Miccaiah et al RTSS'15. 0 for level-A (no CPMD for cyclic executive)

    CPI_PER_UNIT = [0, 0, 0]#assumed to be small

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

    MIN_SAMPLES = 1#50
    MAX_SAMPLES = 1#200 #set at 2 for initial testing
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

    '''
    observation: making this 1 makes systems less schedulable,
    despite 1 being the best choice to minimize total util
    Best choice is dependent on the number of threads/ cluster?
    Also, easier to just change the constant value as an input parameter than working into scenario parameters.
    MAX_THREADED_UTIL: Dict[str, float] = {
        'Max_Threaded_Util_1.0': 1.0,
        'Max_Threaded_Util_0.75': 0.75,
        'Max_Threaded_Util_0.5': 0.5
    }
    '''
    # As used in the RTSS'20 and RTAS'21 submissions
    MAX_THREADED_UTIL = 0.5

    # These are normal distributions which when sampled produce a fractional multiplier to a
    # task's Level-A cost which yields the Level-B or Level-C cost when applied. Level-A should
    # always have a distribution centered at 1 with standard deviation 0.
    # Note that if the sampled multiplier is greater than 1, it's automatically set to 1 (so large
    # standard deviations are safe).
    # Input is (mean, stdev, min).
    # Disabled for the RTAS'21 paper as it is excessively optimistic at Level-A. -Joshua
    #CRIT_SENSITIVITY: Dict[str, Dict[int,Tuple[float,float,float]]] = {
    #    'Default_Crit_Sensitivity': {LEVEL_A: (1.0, 0.0, 0.0), LEVEL_B: (0.74, 0.24, 0.37), LEVEL_C: (0.63, 0.25, 0.13)} # TACLe-based: 10M vs 100k vs 1k sample maximum differences
    #}

    # for all of the following, abreviated versions with the same name may be useful for debugging.

    # from RTSS '15
    CRITICALITY_UTIL_DIST: Dict[str, Dict[int,Tuple[float,float]]] = {
        'C-Heavy':      {LEVEL_A: LIGHT_RATIO, LEVEL_B: LIGHT_RATIO, LEVEL_C: HEAVY_RATIO},
       # 'C-All':        {LEVEL_A: (0.0, 0.0), LEVEL_B: (0.0,0.0), LEVEL_C: (1.0,1.0)},
       # 'C-None':       {LEVEL_A: (0.4,0.6), LEVEL_B: (0.4,0.6), LEVEL_C: (0.0,0.0)},
       # 'B-Heavy':      {LEVEL_A: LOW_MODERATE_RATIO, LEVEL_B: HEAVY_RATIO, LEVEL_C: LIGHT_RATIO},
        'AB-Moderate':  {LEVEL_A: HIGH_MODERATE_RATIO, LEVEL_B: HIGH_MODERATE_RATIO, LEVEL_C: LIGHT_RATIO},
    }


    # Each tuple contains a list of all selectable periods for that level/configuration pair.
    # Note that all Level-B periods MUST be an even multiple of the Level-A hyperperiod for the
    # MC^2 scheduler to work.
    PERIOD_DIST: Dict[str, Dict[int,Tuple[int,int]]] = { #in ms, converted to us in Task generation
        'Many':         {LEVEL_A: (5, 10, 20), LEVEL_B: (20, 40, 80, 160), LEVEL_C: (10, 100)}, # From MC^2 meeting on 06/17
        'Short':        {LEVEL_A: (3, 6), LEVEL_B: (6, 12), LEVEL_C: (3, 33)},      # From RTSS'15
        'Contrasting':  {LEVEL_A: (3, 6), LEVEL_B: (96, 192), LEVEL_C: (10, 100)},  # From RTSS'15
        'Long':         {LEVEL_A: (48, 96), LEVEL_B: (96, 192), LEVEL_C: (50, 500)} # From RTSS'15
    }

    # from RTSS '15
    TASK_UTIL: Dict[str, Dict[int,Tuple[float,float]]] = {
        'Heavy_Util':    {LEVEL_A: (0.1, 0.2), LEVEL_B: (0.2, 0.4), LEVEL_C: (0.4, 0.6)},
        'Moderate_Util': {LEVEL_A: (0.02, 0.1), LEVEL_B: (0.05, 0.2), LEVEL_C: (0.1, 0.4)},
        'Light_Util':    {LEVEL_A: (0.001, 0.03), LEVEL_B: (0.001, 0.05), LEVEL_C: (0.001, 0.1)}
    }

    # Informed by benchmarks
    CACHE_SENSITIVITY: Dict[str, Tuple[float,float,float]] = {
         'Default_Sensitivity':   (1.16, 2.95, 15.68) # DIS-based; pre-rewrite and reparameterization of matrix/neighborhood stressmarks
    }

    # units are MB
    # Normal distribution with tuple format: (mean, stdev)
    # Negative values are truncated to 0
    WSS_DIST: Dict[str, Tuple[float,float]] = {
        'Default_WSS': (2.0, 2.0) # From MC^2 meeting on 06/24
    }

    # Tuples are (mean, standard deviation, 0) for Level-C and (mean, stdev, unfriendliness chance)
    # for Level-A and Level-B. The "unfriendliness chance" is the probability described on page 7,
    # paragraph 2 of Sims's RTCSA'20 paper - set it to 0 to disable.
    # Oct 25 2020, Note: Unfriendliness chance is disabled because we just naturally let the normal
    #                    distribution generate values >2 -Joshua
    SMT_EFFECTIVENESS_DIST: Dict[str, Dict[int,Tuple[float,float,float]]] = {
        'DIS_SMTv2':   {LEVEL_A: (.30, .17, .05), LEVEL_B: (.30, .17, .05), LEVEL_C: (1.60, .54, 0)}, # A/B: DIS-based; 10x diff, <=0, >1 removed and >1 modeled. C: DIS-based w/out coloring
        'TACLE_SMTv2': {LEVEL_A: (.40, .21, .15), LEVEL_B: (.40, .21, .15), LEVEL_C: (1.79, .32, 0)}, # A/B: SD-VBS-based; 10x diff, <=0, >1 removed and >1 modeled. C: TACLe-based w/out coloring
        'SDVBS_SMTv2': {LEVEL_A: (.52, .17, .05), LEVEL_B: (.52, .17, .05), LEVEL_C: (1.72, .13, 0)}, # A/B: TACLe-based; 10x diff, <=0, >1 removed and >1 modeled. C: SD-VBS-based w/out coloring
        'Prior_SMTv2': {LEVEL_A: (.60, .07, .20), LEVEL_B: (.60, .07, .20), LEVEL_C: (1.80, .10, 0)}, # A/B/C: From prior work
        'TACLE_v_SDVBS_SMTv2': {LEVEL_A: (.40, .21, .15), LEVEL_B: (.40, .21, .15), LEVEL_C: (1.72, .13, 0)}, # A/B: From TACLe (above). C: From SD-VBS (above)
        # 'None':     {LEVEL_A: (2.0, 0.0, 1.0), LEVEL_B: (2.0, 0.0, 1.0), LEVEL_C: (3.0, 0.0, 0)}
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

    SMT_EFFECTIVENESS_AB_CASE_STUDY = {
        'DIS':{'field': {'field': 0.4, 'matrix': 0.108, 'neighborhood': 0.478, 'pointer': 0.335, 'transitive': -0.59, 'update': 0.56}, 'matrix': {'field': 0.108, 'matrix': 60, 'neighborhood': 0.493, 'pointer': 60, 'transitive': 60, 'update': 1.27}, 'neighborhood': {'field': 0.478, 'matrix': 0.493, 'neighborhood': 60, 'pointer': 0.303, 'transitive': 0.2, 'update': 0.334}, 'pointer': {'field': 0.335, 'matrix': 60, 'neighborhood': 0.303, 'pointer': 60, 'transitive': 0.0511, 'update': 0.04}, 'transitive': {'field': -0.59, 'matrix': 60, 'neighborhood': 0.2, 'pointer': 0.0511, 'transitive': 60, 'update': 0.436}, 'update': {'field': 0.56, 'matrix': 1.27, 'neighborhood': 0.334, 'pointer': 0.04, 'transitive': 0.436, 'update': 1.81}},
        'TACLe':{'h264_dec': {'h264_dec': 0.257, 'huff_dec': 0.0842, 'cjpeg_wrbm': 0.2, 'fmref': 0.118, 'audiobeam': -0.201, 'adpcm_dec': 0.178, 'adpcm_enc': 0.147, 'g723_enc': 0.0543, 'huff_enc': 0.321, 'gsm_dec': 0.135, 'cjpeg_tran': 0.253, 'epic': 3.06, 'anagram': 0.258, 'rijndael_e': 0.405, 'rijndael_d': 1.8, 'gsm_enc': 0.767, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'huff_dec': {'h264_dec': 0.0842, 'huff_dec': 0.362, 'cjpeg_wrbm': -0.412, 'fmref': 0.399, 'audiobeam': -0.141, 'adpcm_dec': 0.155, 'adpcm_enc': -0.036, 'g723_enc': 0.0579, 'huff_enc': 0.18, 'gsm_dec': 0.238, 'cjpeg_tran': 0.268, 'epic': 0.708, 'anagram': 0.226, 'rijndael_e': 0.231, 'rijndael_d': 1.51, 'gsm_enc': 0.756, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'cjpeg_wrbm': {'h264_dec': 0.2, 'huff_dec': -0.412, 'cjpeg_wrbm': 0.589, 'fmref': 0.934, 'audiobeam': -0.297, 'adpcm_dec': 0.112, 'adpcm_enc': -0.256, 'g723_enc': 0.456, 'huff_enc': -0.0312, 'gsm_dec': 0.233, 'cjpeg_tran': 0.433, 'epic': 1.06, 'anagram': 0.314, 'rijndael_e': 0.502, 'rijndael_d': 3.1, 'gsm_enc': 1.31, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'fmref': {'h264_dec': 0.118, 'huff_dec': 0.399, 'cjpeg_wrbm': 0.934, 'fmref': 0.246, 'audiobeam': -0.18, 'adpcm_dec': 0.0899, 'adpcm_enc': -0.0644, 'g723_enc': -0.0725, 'huff_enc': 0.619, 'gsm_dec': 0.238, 'cjpeg_tran': 0.537, 'epic': 0.827, 'anagram': 0.119, 'rijndael_e': 0.863, 'rijndael_d': 2.49, 'gsm_enc': 1.15, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'audiobeam': {'h264_dec': -0.201, 'huff_dec': -0.141, 'cjpeg_wrbm': -0.297, 'fmref': -0.18, 'audiobeam': 0.013, 'adpcm_dec': -0.281, 'adpcm_enc': -0.133, 'g723_enc': -0.0182, 'huff_enc': 0.0689, 'gsm_dec': 0.159, 'cjpeg_tran': 0.215, 'epic': 0.497, 'anagram': 0.215, 'rijndael_e': 0.214, 'rijndael_d': 1.22, 'gsm_enc': 0.542, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'adpcm_dec': {'h264_dec': 0.178, 'huff_dec': 0.155, 'cjpeg_wrbm': 0.112, 'fmref': 0.0899, 'audiobeam': -0.281, 'adpcm_dec': 0.678, 'adpcm_enc': 0.394, 'g723_enc': 0.18, 'huff_enc': 0.164, 'gsm_dec': 0.294, 'cjpeg_tran': 0.35, 'epic': 0.589, 'anagram': 0.181, 'rijndael_e': 0.237, 'rijndael_d': 1.62, 'gsm_enc': 1.0, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'adpcm_enc': {'h264_dec': 0.147, 'huff_dec': -0.036, 'cjpeg_wrbm': -0.256, 'fmref': -0.0644, 'audiobeam': -0.133, 'adpcm_dec': 0.394, 'adpcm_enc': 0.289, 'g723_enc': -0.128, 'huff_enc': 0.285, 'gsm_dec': 0.294, 'cjpeg_tran': 0.311, 'epic': 0.628, 'anagram': 0.184, 'rijndael_e': 0.344, 'rijndael_d': 1.56, 'gsm_enc': 0.65, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'g723_enc': {'h264_dec': 0.0543, 'huff_dec': 0.0579, 'cjpeg_wrbm': 0.456, 'fmref': -0.0725, 'audiobeam': -0.0182, 'adpcm_dec': 0.18, 'adpcm_enc': -0.128, 'g723_enc': 0.312, 'huff_enc': 0.176, 'gsm_dec': 0.223, 'cjpeg_tran': 0.432, 'epic': 0.493, 'anagram': 0.2, 'rijndael_e': 0.322, 'rijndael_d': 1.21, 'gsm_enc': 0.644, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'huff_enc': {'h264_dec': 0.321, 'huff_dec': 0.18, 'cjpeg_wrbm': -0.0312, 'fmref': 0.619, 'audiobeam': 0.0689, 'adpcm_dec': 0.164, 'adpcm_enc': 0.285, 'g723_enc': 0.176, 'huff_enc': 0.352, 'gsm_dec': 0.251, 'cjpeg_tran': 0.395, 'epic': 0.549, 'anagram': 0.324, 'rijndael_e': 0.327, 'rijndael_d': 1.47, 'gsm_enc': 0.866, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'gsm_dec': {'h264_dec': 0.135, 'huff_dec': 0.238, 'cjpeg_wrbm': 0.233, 'fmref': 0.238, 'audiobeam': 0.159, 'adpcm_dec': 0.294, 'adpcm_enc': 0.294, 'g723_enc': 0.223, 'huff_enc': 0.251, 'gsm_dec': 0.451, 'cjpeg_tran': 0.492, 'epic': 0.437, 'anagram': 0.292, 'rijndael_e': 0.406, 'rijndael_d': 0.717, 'gsm_enc': 0.526, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'cjpeg_tran': {'h264_dec': 0.253, 'huff_dec': 0.268, 'cjpeg_wrbm': 0.433, 'fmref': 0.537, 'audiobeam': 0.215, 'adpcm_dec': 0.35, 'adpcm_enc': 0.311, 'g723_enc': 0.432, 'huff_enc': 0.395, 'gsm_dec': 0.492, 'cjpeg_tran': 0.596, 'epic': 0.509, 'anagram': 0.311, 'rijndael_e': 0.418, 'rijndael_d': 0.64, 'gsm_enc': 0.515, 'susan': 60, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'epic': {'h264_dec': 3.06, 'huff_dec': 0.708, 'cjpeg_wrbm': 1.06, 'fmref': 0.827, 'audiobeam': 0.497, 'adpcm_dec': 0.589, 'adpcm_enc': 0.628, 'g723_enc': 0.493, 'huff_enc': 0.549, 'gsm_dec': 0.437, 'cjpeg_tran': 0.509, 'epic': 0.591, 'anagram': 0.366, 'rijndael_e': 0.484, 'rijndael_d': 0.578, 'gsm_enc': 0.456, 'susan': 2.03, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'anagram': {'h264_dec': 0.258, 'huff_dec': 0.226, 'cjpeg_wrbm': 0.314, 'fmref': 0.119, 'audiobeam': 0.215, 'adpcm_dec': 0.181, 'adpcm_enc': 0.184, 'g723_enc': 0.2, 'huff_enc': 0.324, 'gsm_dec': 0.292, 'cjpeg_tran': 0.311, 'epic': 0.366, 'anagram': 0.303, 'rijndael_e': 0.342, 'rijndael_d': 0.508, 'gsm_enc': 0.437, 'susan': 3.6, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'rijndael_e': {'h264_dec': 0.405, 'huff_dec': 0.231, 'cjpeg_wrbm': 0.502, 'fmref': 0.863, 'audiobeam': 0.214, 'adpcm_dec': 0.237, 'adpcm_enc': 0.344, 'g723_enc': 0.322, 'huff_enc': 0.327, 'gsm_dec': 0.406, 'cjpeg_tran': 0.418, 'epic': 0.484, 'anagram': 0.342, 'rijndael_e': 1.25, 'rijndael_d': 0.876, 'gsm_enc': 0.497, 'susan': 1.99, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'rijndael_d': {'h264_dec': 1.8, 'huff_dec': 1.51, 'cjpeg_wrbm': 3.1, 'fmref': 2.49, 'audiobeam': 1.22, 'adpcm_dec': 1.62, 'adpcm_enc': 1.56, 'g723_enc': 1.21, 'huff_enc': 1.47, 'gsm_dec': 0.717, 'cjpeg_tran': 0.64, 'epic': 0.578, 'anagram': 0.508, 'rijndael_e': 0.876, 'rijndael_d': 1.16, 'gsm_enc': 0.516, 'susan': 2.02, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'gsm_enc': {'h264_dec': 0.767, 'huff_dec': 0.756, 'cjpeg_wrbm': 1.31, 'fmref': 1.15, 'audiobeam': 0.542, 'adpcm_dec': 1.0, 'adpcm_enc': 0.65, 'g723_enc': 0.644, 'huff_enc': 0.866, 'gsm_dec': 0.526, 'cjpeg_tran': 0.515, 'epic': 0.456, 'anagram': 0.437, 'rijndael_e': 0.497, 'rijndael_d': 0.516, 'gsm_enc': 0.613, 'susan': 1.92, 'dijkstra': 60, 'ammunition': 60, 'mpeg2': 60}, 'susan': {'h264_dec': 60, 'huff_dec': 60, 'cjpeg_wrbm': 60, 'fmref': 60, 'audiobeam': 60, 'adpcm_dec': 60, 'adpcm_enc': 60, 'g723_enc': 60, 'huff_enc': 60, 'gsm_dec': 60, 'cjpeg_tran': 60, 'epic': 2.03, 'anagram': 3.6, 'rijndael_e': 1.99, 'rijndael_d': 2.02, 'gsm_enc': 1.92, 'susan': 0.847, 'dijkstra': 0.337, 'ammunition': 0.423, 'mpeg2': 1.18}, 'dijkstra': {'h264_dec': 60, 'huff_dec': 60, 'cjpeg_wrbm': 60, 'fmref': 60, 'audiobeam': 60, 'adpcm_dec': 60, 'adpcm_enc': 60, 'g723_enc': 60, 'huff_enc': 60, 'gsm_dec': 60, 'cjpeg_tran': 60, 'epic': 60, 'anagram': 60, 'rijndael_e': 60, 'rijndael_d': 60, 'gsm_enc': 60, 'susan': 0.337, 'dijkstra': 0.271, 'ammunition': 0.386, 'mpeg2': 0.596}, 'ammunition': {'h264_dec': 60, 'huff_dec': 60, 'cjpeg_wrbm': 60, 'fmref': 60, 'audiobeam': 60, 'adpcm_dec': 60, 'adpcm_enc': 60, 'g723_enc': 60, 'huff_enc': 60, 'gsm_dec': 60, 'cjpeg_tran': 60, 'epic': 60, 'anagram': 60, 'rijndael_e': 60, 'rijndael_d': 60, 'gsm_enc': 60, 'susan': 0.423, 'dijkstra': 0.386, 'ammunition': 0.541, 'mpeg2': 0.64}, 'mpeg2': {'h264_dec': 60, 'huff_dec': 60, 'cjpeg_wrbm': 60, 'fmref': 60, 'audiobeam': 60, 'adpcm_dec': 60, 'adpcm_enc': 60, 'g723_enc': 60, 'huff_enc': 60, 'gsm_dec': 60, 'cjpeg_tran': 60, 'epic': 60, 'anagram': 60, 'rijndael_e': 60, 'rijndael_d': 60, 'gsm_enc': 60, 'susan': 1.18, 'dijkstra': 0.596, 'ammunition': 0.64, 'mpeg2': 0.817}}

    }


    SMT_EFFECTIVENESS_C_CASE_STUDY = {
        'DIS': {
            "neighborhood": 1.24,
            'pointer': 1.19,
            'transitive': 1.1,
            'update': 1.19
        },
        'SD-VBS': {
            'disparity':    1.79,
            'localization':   1.91,
            'mser':   1.55,
            'sift':   1.57,
            'stitch':   1.73,
            'svm':   1.59,
            'texture_synt':   1.7,
            'tracking':   1.89
        }
    }

    BENCHMARK_FULL_NAME = {
        'TACLe': {
            'petrinet': 'petrinet',
           'statemate': 'statemate',
           'ndes': 'ndes',
           'huff_dec': 'huff_dec',
           'cjpeg_wrbm': 'cjpeg_wrbmp',
           'h264_dec': 'h264_dec',
           'fmref': 'fmref',
           'adpcm_dec': 'adpcm_dec',
           'adpcm_enc': 'adpcm_enc',
           'g723_enc': 'g723_enc',
           'audiobeam': 'audiobeam',
           'huff_enc': 'huff_enc',
           'gsm_dec': 'gsm_dec',
           'cjpeg_tran': 'cjpeg_transupp',
           'epic': 'epic',
           'rijndael_e': 'rijndael_enc',
           'anagram': 'anagram',
           'rijndael_d': 'rijndael_dec',
           'gsm_enc': 'gsm_enc',
           'susan': 'susan',
           'dijkstra': 'dijkstra',
           'ammunition': 'ammunition',
           'mpeg2': 'mpeg2'
        },
        'SD-VBS': {
            'disparity': 'disparity_qcif',
            'localization': 'localization_qcif',
            'mser': 'mser_qcif',
            'sift': 'sift_qcif',
            'stitch': 'stitch_qcif',
            'svm': 'svm_qcif',
            'texture_synt': 'texture_synthesis_qcif',
            'tracking': 'tracking_qcif'
        }
    }

    wcet_map = {
        'SD-VBS': {
            'texture_synt': 3.500985,
            'mser': 4.576398999999999,
            'tracking': 6.142087999999999,
            'disparity': 12.30912,
            'localization': 21.962538,
            'stitch': 22.805571999999998,
            'svm': 25.137069999999998,
            'sift': 36.1697,
            'multi_ncut': 4861.814272
        },
        'DIS': {
            'neighborhood': 98.87772799999999,
            'field': 368.512,
            'matrix': 895.50112,
            'update': 921.9066879999999,
            'pointer': 1219.6355839999999,
            'transitive': 1251.7841919999998
        },
        'TACLe': {
            'petrinet': 0.003702,
            'statemate': 0.037925,
            'cjpeg_wrbm': 0.042533999999999995,
            'ndes': 0.044979,
            'fmref': 0.052031999999999995,
            'h264_dec': 0.07710499999999999,
            'huff_dec': 0.07955,
            'adpcm_dec': 0.08374,
            'adpcm_enc': 0.08520699999999999,
            'g723_enc': 0.09987399999999999,
            'huff_enc': 0.105391,
            'audiobeam': 0.11251499999999999,
            'gsm_dec': 0.165595,
            'cjpeg_tran': 0.181169,
            'epic': 0.22516899999999998,
            'rijndael_e': 0.240814,
            'rijndael_d': 0.24975399999999998,
            'anagram': 0.25589999999999996,
            'gsm_enc': 0.31554499999999996,
            'susan': 1.904305,
            'dijkstra': 3.819016,
            'ammunition': 8.924935999999999,
            'mpeg2': 11.445241
        }
    }

    acet_map = {
        'SD-VBS': {
            'texture_synt': 3.2601419999999997,
            'mser': 4.316075,
            'tracking': 5.201947,
            'disparity': 11.753719,
            'stitch': 17.282014,
            'localization': 20.316338,
            'svm': 24.342458999999998,
            'sift': 34.437774,
            'multi_ncut': 4860.693216
        },
        'DIS': {
            'neighborhood': 95.04602799999999,
            'field': 366.58606499999996,
            'matrix': 628.577951,
            'update': 916.460487,
            'transitive': 1032.6602269999998,
            'pointer': 1207.138986
        },
        'TACLe': {
            'petrinet': 0.002012,
            'statemate': 0.006965,
            'ndes': 0.015097,
            'huff_dec': 0.019037,
            'cjpeg_wrbm': 0.020166,
            'h264_dec': 0.020307,
            'fmref': 0.028489,
            'adpcm_dec': 0.034856,
            'adpcm_enc': 0.035722,
            'g723_enc': 0.039626,
            'audiobeam': 0.040182999999999996,
            'huff_enc': 0.054422,
            'gsm_dec': 0.11111,
            'cjpeg_tran': 0.128642,
            'epic': 0.17216299999999998,
            'rijndael_e': 0.19980499999999998,
            'anagram': 0.20346499999999998,
            'rijndael_d': 0.207398,
            'gsm_enc': 0.272698,
            'susan': 1.711844,
            'dijkstra': 3.7653179999999997,
            'ammunition': 8.770932,
            'mpeg2': 11.36022
        }
    }

    cacheSensitivityMapping = {'SD-VBS': {}, 'DIS': {}, 'TACLe': {}}

    cacheSensitivityMapping['DIS'] = {
        'field': 1.16,
        'matrix': 15.68,
        'neighborhood': 2.95,
        'pointer': 1.16,
        'transitive': 15.68,
        'update': 1.16
    }

    cacheSensitivityMapping['SD-VBS'] = {
        'texture_synt': 2.95,
        'mser': 2.95,
        'tracking': 15.68,
        'disparity': 15.68,
        'stitch': 15.68,
        'localization': 2.95,
        'svm': 2.95,
        'sift': 2.95,
        'multi_ncut': 2.95
    }

    cacheSensitivityMapping['TACLe'] = {
        'adpcm_dec': 1.16,
        'adpcm_enc': 1.16,
        'ammunition': 1.16,
        'cjpeg_tran': 1.16,
        'cjpeg_wrbm': 1.16,
        'dijkstra': 1.16,
        'epic': 1.16,
        'fmref': 1.16,
        'gsm_dec': 1.16,
        'gsm_enc': 1.16,
        'h264_dec': 1.16,
        'huff_enc': 1.16,
        'mpeg2': 1.16,
        'ndes': 1.16,
        'petrinet': 1.16,
        'rijndael_d': 1.16,
        'rijndael_e': 1.16,
        'statemate': 1.16,
        'susan': 1.16,
        'huff_dec': 1.16,
        'g723_enc': 1.16,
        'audiobeam': 1.16,
        'anagram': 1.16
    }
