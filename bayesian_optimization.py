###
# Adapted from the BoTorch Multi-Objective Bayesian Optimization Tutorial:
# https://botorch.org/tutorials/multi_objective_bo
###

import torch
from botorch import fit_gpytorch_mll
from botorch.sampling.samplers import SobolQMCNormalSampler
from botorch.models.gp_regression import SingleTaskGP
from botorch.models.model_list_gp_regression import ModelListGP
from botorch.models.transforms.outcome import Standardize
from gpytorch.mlls.sum_marginal_log_likelihood import SumMarginalLogLikelihood
from botorch.utils.transforms import unnormalize, normalize
from botorch.utils.sampling import draw_sobol_samples
from botorch.optim.optimize import optimize_acqf
from botorch.acquisition.multi_objective.monte_carlo import qNoisyExpectedHypervolumeImprovement

import config

tkwargs = {
    "dtype": torch.double,
    "device": torch.device("cuda" if torch.cuda.is_available() else "cpu"),
}

if torch.cuda.is_available():
    print("Using CUDA acceleration for Bayesian Optimization")

bounds = torch.tensor(config.bounds, **tkwargs)

standard_bounds = torch.zeros(2, 2, **tkwargs)
standard_bounds[1] = 1
ref_point = torch.tensor((300, 200), **tkwargs)

def initial_points(n=10):
    points = draw_sobol_samples(bounds=bounds,n=n, q=1).squeeze(1)
    return points

def initialize_model(train_x, train_obj):
    # define models for objective and constraint
    train_x = normalize(train_x, bounds)
    models = []
    for i in range(train_obj.shape[-1]):
        train_y = train_obj[..., i:i+1]
        models.append(
            SingleTaskGP(train_x, train_y, outcome_transform=Standardize(m=1))
        )
    model = ModelListGP(*models)
    mll = SumMarginalLogLikelihood(model.likelihood, model)
    return mll, model

BATCH_SIZE = 4
NUM_RESTARTS = 10
RAW_SAMPLES = 512
MC_SAMPLES = 128

def optimize_qnehvi_and_get_candidate(model, mll, train_x):
    """Optimizes the qNEHVI acquisition function, and returns a new candidate."""
    # fit the model
    fit_gpytorch_mll(mll)
    # create sampler
    sampler = SobolQMCNormalSampler(num_samples=MC_SAMPLES)
    # partition non-dominated space into disjoint rectangles
    acq_func = qNoisyExpectedHypervolumeImprovement(
        model=model,
        ref_point= ref_point.tolist(),  # use known reference point 
        X_baseline=normalize(train_x, bounds),
        prune_baseline=True,  # prune baseline points that have estimated zero probability of being Pareto optimal
        sampler=sampler,
    )
    # optimize
    candidates, _ = optimize_acqf(
        acq_function=acq_func,
        bounds=standard_bounds,
        q=BATCH_SIZE,
        num_restarts=NUM_RESTARTS,
        raw_samples=RAW_SAMPLES,  # used for intialization heuristic
        options={"batch_limit": 5, "maxiter": 200},
        sequential=True,
    )
    # observe new values 
    new_x = unnormalize(candidates.detach(), bounds=bounds)
    return new_x