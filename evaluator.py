#!/usr/bin/env python
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from user_model import SVMUserModel
from teacher import RandomTeacher, GridTeacher, OptimalTeacher
from history import History
from ground_truth import GroundTruth, error_to_accuracy

class Settings(object):
    def __init__(self, DIM, N_EXAMPLES):
        self.DIM = DIM
        self.N_EXAMPLES = N_EXAMPLES
        self.LOCATIONS = self.compute_locations()
        self.GRID_CMAP = matplotlib.colors.ListedColormap(['dimgray', 'silver'])

    def compute_locations(self):
        D = len(self.DIM)
        coords_by_dim = [range(b) for b in self.DIM]
        locations = np.vstack(np.meshgrid(*coords_by_dim)).reshape(D, -1).T
        return [tuple(loc) for loc in locations]


class TeacherConfig(object):
    def __init__(self, teacher, reps):
        self.teacher = teacher
        self.reps = reps


# Run active learning with given teacher. User behaves according to user model.
def run(settings, user_model, teacher):
    print "Running active learning with %s and %s" % \
        (user_model.__class__.__name__, teacher.__class__.__name__)

    history = History(user_model.prior)
    for i in range(settings.N_EXAMPLES):
        example = teacher.next_example(history)
        history.add_example(example)
        prediction = user_model.predict_grid(history.examples)
        history.add_prediction(prediction)
        # print "examples: " + str(history.examples)
        # print prediction

    if len(settings.DIM) == 2:
        # plotting history only supported for two dimensions
        history.plot(filename="%s-%s" % (user_model.name, teacher.name),
            title="Active learning with %s user model, %s teacher" % (user_model.name, teacher.name),
            settings=settings)
    return history

def compute_teacher_accuracies(settings, user_model, teacher, ground_truth):
    history = run(settings, user_model, teacher)
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
                ('%s-median' % teacher_name, np.percentile(all_reps, 50, axis=0)),
                ('%s-p05' % teacher_name, np.percentile(all_reps, 5, axis=0)),
                ('%s-p95' % teacher_name, np.percentile(all_reps, 95, axis=0))
            ]

    return teacher_accuracies

def plot_teacher_accuracy(teacher_accuracies, filename, title):
    plt.figure()

    for name, accuracies in teacher_accuracies:
        plt.plot(range(1, len(accuracies)+1), accuracies, label=name, linestyle='-', linewidth=2)

    axes = plt.gca()
    axes.set_ylim([0, 1.1])

    plt.xlabel("Teaching examples")
    plt.ylabel("Accuracy")
    plt.title(title)
    plt.legend(loc='lower right')

    fig = plt.gcf()
    fig.set_size_inches(6, 6)
    fig.savefig('%s.png' % filename, dpi=100)

    plt.close()

# Simulate user behaving exactly according to user model. Compare teachers.
def eval_teachers_assuming_user_model():
    settings = Settings(DIM=(4, 4, 4), N_EXAMPLES=27)

    ground_truth = GroundTruth(settings)
    ground_truth.plot()

    user_model = SVMUserModel(settings)
    random_teacher = RandomTeacher(settings, ground_truth)
    grid_teacher = GridTeacher(settings, ground_truth)
    optimal_teacher = OptimalTeacher(settings, ground_truth, user_model)

    teacher_configs = [
        TeacherConfig(random_teacher, 10),
        TeacherConfig(grid_teacher, 10),
        TeacherConfig(optimal_teacher, 1)
    ]
    teacher_accuracies = aggregate_teacher_accuracies(settings, user_model, teacher_configs, ground_truth)
    plot_teacher_accuracy(teacher_accuracies, filename='%s-teacher-accuracy' % user_model.name,
        title="Comparison of teacher accuracy with %s user model" % user_model.name)


if __name__ == "__main__":
    eval_teachers_assuming_user_model()
