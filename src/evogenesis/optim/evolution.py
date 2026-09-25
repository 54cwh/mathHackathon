import math
import random


def softmax_selection_probabilities(fitness, beta: float = 3.0):
    scaled = [beta * f for f in fitness]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    z = sum(exps)
    return [x / z for x in exps]


def sample_parent_index(probabilities, rng: random.Random):
    r, c = rng.random(), 0.0
    for i, p in enumerate(probabilities):
        c += p
        if r <= c:
            return i
    return len(probabilities) - 1
