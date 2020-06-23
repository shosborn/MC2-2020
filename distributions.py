import random
import numpy.random
from typing import Tuple, TypeVar

T = TypeVar('T')

def sample_unif_distribution(unif_range: Tuple[float,float]) -> float :
    return random.uniform(unif_range[0], unif_range[1])

def sample_unif_int_distribution(unif_range: Tuple[int,int]) -> int :
    return random.randint(unif_range[0],unif_range[1])

def sample_choice(choices: Tuple[T, ...]) -> T :
    return random.choice(choices)

def sample_normal_dist(mean: float, std: float) -> float :
    return numpy.random.normal(mean, std)