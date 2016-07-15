#!/usr/bin/env python

import math
import matplotlib.pyplot as plt
import numpy as np


def plot_ground_truth(ground_truth):
    settings = ground_truth.settings
    if len(settings.DIM) > 2:
        # plotting ground truth only supported for two dimensions
        return

    plt.figure()

    plt.axis('off')
    plt.title("Ground truth: %s grid with\n%s" % (settings.dim_string(), str(ground_truth)))
    plt.imshow(ground_truth.grid.T, cmap=settings.GRID_CMAP, interpolation='none', origin='lower')

    fig = plt.gcf()
    fig.set_size_inches(6, 4)
    fig.savefig('%s/%s-ground-truth.png' % (settings.RUN_DIR, ground_truth.name), dpi=100)

    plt.close()


# plot a model evaluated at all grid locations
def plot_evaluation(evaluation, filename, title, settings):
    if len(settings.DIM) > 2:
        # plotting evaluation only supported for two dimensions
        return

    plt.figure()

    plt.axis('off')
    plt.title(title)
    plt.imshow(evaluation.T, cmap="YlOrRd", origin='lower', vmin=0.0, vmax=1.0)
    # plt.colorbar()

    # plot contours
    # coords_by_dim = [range(b) for b in settings.DIM]
    # X, Y = np.meshgrid(*coords_by_dim)
    # contour_set = plt.contour(X, Y, evaluation.T, colors='k', origin='lower')
    # plt.clabel(contour_set, inline=1, fontsize=10)

    fig = plt.gcf()
    fig.set_size_inches(6, 4)
    fig.savefig('%s.png' % filename, dpi=100)

    plt.close()


def plot_history(history, filename, title, settings):
    if len(settings.DIM) > 2:
        # plotting history only supported for two dimensions
        return

    def plot_iteration(i, settings):
        prediction = history.predictions[i]

        plt.axis('off')
        plt.title("Prediction after %d iterations" % (i+1))
        # label=0 is dark gray, label=1 is silver
        plt.imshow(prediction.T, cmap=settings.GRID_CMAP, interpolation='none', origin='lower')
        for j in range(i+1):
            loc, label = history.examples[j]
            x, y = loc
            c = 'maroon' if j == i else 'black'
            plt.annotate(s=str(j+1), xy=(x, y), color=c)

    plt.figure()
    plt.suptitle(title)

    valid_iter = [i for i in range(len(history.examples)) if history.predictions[i] is not None]
    N = len(valid_iter)
    nrow = int(math.ceil(N/2.0))
    for fignum, i in enumerate(valid_iter):
        plt.subplot(nrow, 2, fignum+1)
        plot_iteration(i, settings)

    fig = plt.gcf()
    fig.set_size_inches(8, 12)
    fig.savefig('%s.png' % filename, dpi=100)

    plt.close()


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
    plt.subplots_adjust(top=0.85)

    fig = plt.gcf()
    fig.set_size_inches(8, 8)
    fig.savefig('%s.png' % filename, dpi=100)

    plt.close()
