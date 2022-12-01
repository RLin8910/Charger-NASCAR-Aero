import random
import numpy

def get_candidate(cur, min_bound, max_bound, step_size):
    """
    Get candidate for simulated annealing step
    """
    candidate = numpy.random.randn(len(cur)) * step_size + cur
    candidate = numpy.minimum(numpy.maximum(candidate, min_bound), max_bound)
    return candidate

def check_accept(cur_eval, can_eval, cur_iter, temp):
    """
    Determine whether to accept the candidate value
    """
    diff = can_eval - cur_eval
    t = temp / float(cur_iter + 1)
    metropolis = numpy.exp(-diff / t)

    return diff < 0 or numpy.random.rand() < metropolis

def objective(target, val):
    dist = numpy.linalg.norm(numpy.array(target) - numpy.array(val))
    return dist*dist