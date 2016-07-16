#!/usr/bin/env python
import argparse
import datetime
import math
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
import random
import shutil
from timeit import default_timer as timer

from user_model import *
from teacher import RandomTeacher, GridTeacher, OptimalTeacher
from ground_truth import *
from viz import *


class Settings(object):
    def __init__(self, DIM, N_EXAMPLES, RUN_DIR, TEACHER_REPS):
        self.DIM = DIM
        self.N_EXAMPLES = N_EXAMPLES
        self.RUN_DIR = RUN_DIR
        self.TEACHER_REPS = TEACHER_REPS
        self.LOCATIONS = self.compute_locations()
        self.GRID_CMAP = matplotlib.colors.ListedColormap(['dimgray', 'silver'])

    def compute_locations(self):
        D = len(self.DIM)
        coords_by_dim = [range(b) for b in self.DIM]
        locations = np.vstack(np.meshgrid(*coords_by_dim)).reshape(D, -1).T
        return [tuple(loc) for loc in locations]

    def dim_string(self):
        return 'x'.join([str(b) for b in self.DIM])

    def uniform_prior(self, p=0.5):
        prior = np.empty(self.DIM)
        prior.fill(p)
        return prior


class History(object):
    def __init__(self, user_prior):
        self.prior = user_prior
        self.examples = []    # teaching examples ((x, y), 0/1)
        self.predictions = []    # user predictions of grid labels (0/1 array)
        self.evaluations = []    # user evaluations of grid labels (array of values in [0,1])

    def add_example(self, example):
        self.examples.append(example)

    def add_prediction_result(self, prediction_result):
        self.predictions.append(prediction_result.prediction)
        if prediction_result.evaluation is not None:
            self.evaluations.append(prediction_result.evaluation)


class TeacherConfig(object):
    def __init__(self, teacher, reps):
        self.teacher = teacher
        self.reps = reps


class Function(object):
    def __init__(self, f, name, formula):
        self.f = f
        self.name = name
        self.formula = formula


# Run active learning with given teacher. User behaves according to user model.
def run(settings, user_model, teacher, ground_truth):
    start_time = timer()
    print "Running active learning with %s grid, %s user model, %s teacher" % \
        (ground_truth.name, user_model.name, teacher.name)

    history = History(user_model.prior)
    for i in range(settings.N_EXAMPLES):
        example = teacher.next_example(history)
        history.add_example(example)
        prediction_result = user_model.predict_grid(history.examples)
        history.add_prediction_result(prediction_result)
        # print "examples: " + str(history.examples)
        # print prediction

    end_time = timer()
    print "Took %d seconds" % (end_time - start_time)

    plot_history(
        history=history,
        filename="%s/%s-%s-%s" % (settings.RUN_DIR, ground_truth.name, user_model.name, teacher.name),
        title="Active learning with %s user model, %s teacher\n%s grid with %s" % \
            (user_model.name, teacher.name, settings.dim_string(), str(ground_truth)),
        settings=settings)
    return history


def compute_teacher_accuracies(settings, user_model, teacher, ground_truth):
    history = run(settings, user_model, teacher, ground_truth)
    errors = [ground_truth.prediction_error(prediction) for prediction in history.predictions]
    return [error_to_accuracy(error) for error in errors]


def aggregate_teacher_accuracies(settings, user_model, teacher_configs, ground_truth):
    teacher_accuracies = []
    for config in teacher_configs:
        teacher_name = config.teacher.name
        if config.reps == 1:
            teacher_accuracies.append(
                (teacher_name, compute_teacher_accuracies(settings, user_model, config.teacher, ground_truth))
            )
        else:
            # compute median, 5th and 95th percentiles
            all_reps = np.vstack([compute_teacher_accuracies(
                settings, user_model, config.teacher, ground_truth) for _ in range(config.reps)])
            teacher_accuracies += [
                ('%s-p95' % teacher_name, np.percentile(all_reps, 95, axis=0)),
                ('%s-median' % teacher_name, np.percentile(all_reps, 50, axis=0)),
                ('%s-p05' % teacher_name, np.percentile(all_reps, 5, axis=0))
            ]

    return teacher_accuracies


# Simulate user behaving exactly according to user model. Compare teachers.
def eval_omniscient_teachers(ground_truth, user_model, settings):
    plot_ground_truth(ground_truth)

    if settings.TEACHER_REPS <= 0:
        return

    random_teacher = RandomTeacher(settings, ground_truth, with_replacement=True)
    grid_teacher = GridTeacher(settings, ground_truth, with_replacement=True)
    optimal_teacher = OptimalTeacher(settings, ground_truth, user_model, with_replacement=True)

    teacher_configs = [
        TeacherConfig(random_teacher, settings.TEACHER_REPS),
        TeacherConfig(grid_teacher, settings.TEACHER_REPS),
        TeacherConfig(optimal_teacher, 1)
    ]
    teacher_accuracies = aggregate_teacher_accuracies(settings, user_model, teacher_configs, ground_truth)
    plot_teacher_accuracy(teacher_accuracies, 
        filename='%s/%s-%s-teacher-accuracy' % (settings.RUN_DIR, ground_truth.name, user_model.name),
        title="Comparison of teacher accuracy with %s user model\n%s grid with %s" % \
            (user_model.name, settings.dim_string(), str(ground_truth))
    )


def all_simulations(args):
    # set random seed globally
    random.seed(1234)
    np.random.seed(1234)

    # prepare directory for saving files
    run_dir = datetime.datetime.now().strftime("%Y%m%d %H%M")
    if args.desc:
        run_dir = "%s-%s" % (run_dir, args.desc)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.mkdir(run_dir)

    # define literal ground truth functions
    exp = Function(f=lambda x: math.exp(x)-2, name="exp", formula="e^x - 2")
    sin = Function(f=lambda x: 2*math.sin(x), name="sin", formula="2 * sin(x)")
    xsinx = Function(f=lambda x: x * math.sin(x), name="x sin x", formula="x * sin(x)")

    # other settings
    if args.dry_run:
        teacher_reps = 0    # just generate ground truth
    else:
        teacher_reps = 20

    # run experiments
    settings = Settings(DIM=(13, 6), N_EXAMPLES=16, RUN_DIR=run_dir, TEACHER_REPS=teacher_reps)
    eval_omniscient_teachers(
        ground_truth=GeneralLinearGroundTruth(settings),
        user_model=LinearSVMUserModel(settings),
        settings=settings
    )
    eval_omniscient_teachers(
        ground_truth=GeneralLinearGroundTruth(settings),
        user_model=RBFOKMUserModel(settings, prior=settings.uniform_prior(), eta=0.85, lambda_param=0.05, w=1),
        settings=settings
    )

    # for degree in range(2, 5):
    #     eval_omniscient_teachers(
    #         ground_truth=SimplePolynomialGroundTruth(degree, settings),
    #         user_model=RBFSVMUserModel(settings),
    #         settings=settings
    #     )
    # for fn in [exp, sin, xsinx]:
    #     eval_omniscient_teachers(
    #         ground_truth=SimpleFunctionGroundTruth(settings, fn),
    #         user_model=RBFSVMUserModel(settings),
    #         settings=settings
    #     )

    # settings = Settings(DIM=(5, 5, 5), N_EXAMPLES=27, RUN_DIR=run_dir, TEACHER_REPS=teacher_reps)
    # eval_omniscient_teachers(
    #     ground_truth=GeneralLinearGroundTruth(settings),
    #     user_model=LinearSVMUserModel(settings),
    #     settings=settings
    # )
    # eval_omniscient_teachers(
    #     ground_truth=SimplePolynomialGroundTruth(2, settings),
    #     user_model=RBFSVMUserModel(settings),
    #     settings=settings
    # )

    # settings = Settings(DIM=(3, 3, 3, 3), N_EXAMPLES=32, RUN_DIR=run_dir, TEACHER_REPS=teacher_reps)
    # eval_omniscient_teachers(
    #     ground_truth=GeneralLinearGroundTruth(settings),
    #     user_model=LinearSVMUserModel(settings),
    #     settings=settings
    # )
    # eval_omniscient_teachers(
    #     ground_truth=SimplePolynomialGroundTruth(2, settings),
    #     user_model=RBFSVMUserModel(settings),
    #     settings=settings
    # )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run algorithmic teaching simulations.")
    parser.add_argument('--dry-run', action='store_true', help="only generate ground truth")
    parser.add_argument('--desc', type=str, help="description appended to directory name")
    args = parser.parse_args()

    all_simulations(args)
