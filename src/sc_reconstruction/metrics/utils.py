import numpy as np
from sklearn.metrics import pairwise_distances, mean_squared_error, r2_score
from sklearn.metrics.pairwise import rbf_kernel, polynomial_kernel
import ot
from scipy.stats import spearmanr, pearsonr



def compute_pearson(X, Y):
    pearson = pearsonr(X, Y).correlation
    return pearson


def compute_spearman(X, Y):
    spearman = spearmanr(X, Y).correlation
    return spearman


# Compute MMD (maximum mean discrepancy) using numpy and scikit-learn.
# The original code is from https://github.com/jindongwang/transferlearning/blob/master/code/distance/mmd_numpy_sklearn.py
def mmd_linear(X, Y):
    """MMD using linear kernel (i.e., k(x,y) = <x,y>)
    Note that this is not the original linear MMD, only the reformulated and faster version.
    The original version is:
        def mmd_linear(X, Y):
            XX = np.dot(X, X.T)
            YY = np.dot(Y, Y.T)
            XY = np.dot(X, Y.T)
            return XX.mean() + YY.mean() - 2 * XY.mean()

    Arguments:
        X {[n_sample1, dim]} -- [X matrix]
        Y {[n_sample2, dim]} -- [Y matrix]

    Returns:
        [scalar] -- [MMD value]
    """
    delta = X.mean(0) - Y.mean(0)
    return delta.dot(delta.T)


def mmd_rbf(X, Y, gamma=1.0):
    """MMD using rbf (gaussian) kernel (i.e., k(x,y) = exp(-gamma * ||x-y||^2 / 2))

    Arguments:
        X {[n_sample1, dim]} -- [X matrix]
        Y {[n_sample2, dim]} -- [Y matrix]

    Keyword Arguments:
        gamma {float} -- [kernel parameter] (default: {1.0})

    Returns:
        [scalar] -- [MMD value]
    """
    XX = rbf_kernel(X, X, gamma)
    YY = rbf_kernel(Y, Y, gamma)
    XY = rbf_kernel(X, Y, gamma)
    return XX.mean() + YY.mean() - 2 * XY.mean()


def mmd_poly(X, Y, degree=2, gamma=1, coef0=0):
    """MMD using polynomial kernel (i.e., k(x,y) = (gamma <X, Y> + coef0)^degree)

    Arguments:
        X {[n_sample1, dim]} -- [X matrix]
        Y {[n_sample2, dim]} -- [Y matrix]

    Keyword Arguments:
        degree {int} -- [degree] (default: {2})
        gamma {int} -- [gamma] (default: {1})
        coef0 {int} -- [constant item] (default: {0})

    Returns:
        [scalar] -- [MMD value]
    """
    XX = polynomial_kernel(X, X, degree, gamma, coef0)
    YY = polynomial_kernel(Y, Y, degree, gamma, coef0)
    XY = polynomial_kernel(X, Y, degree, gamma, coef0)
    return XX.mean() + YY.mean() - 2 * XY.mean()




def gene_r_squared(X, Y):
    # Sum features across cells (axis 0) before computing r2_score.
    return r2_score(X.sum(0), Y.sum(0))



def energy_distance(X, Y):
    d_xy = np.mean(pairwise_distances(X, Y, metric='euclidean'))
    d_xx = np.mean(pairwise_distances(X, X, metric='euclidean'))
    d_yy = np.mean(pairwise_distances(Y, Y, metric='euclidean'))
    return 2 * d_xy - d_xx - d_yy



def knn_purity(X_query, X_pert, X_ctrl, k):
    """Fraction of query's k-NN in (pert + ctrl) pool that are perturbed.

    Returns a float in [0, 1]. 1.0 = all neighbors are perturbed,
    0.0 = all control, 0.5 = random baseline (when pool is balanced).
    """
    from sklearn.neighbors import NearestNeighbors

    pool = np.vstack([X_pert, X_ctrl])
    labels = np.concatenate([np.ones(len(X_pert)), np.zeros(len(X_ctrl))])
    k_eff = min(k, len(pool))
    nn = NearestNeighbors(n_neighbors=k_eff, metric="euclidean", algorithm="auto")
    nn.fit(pool)
    indices = nn.kneighbors(X_query, return_distance=False)
    return float(labels[indices].mean())


def sinkhorn_divergence(X, Y, reg=0.1):
    n = X.shape[0]
    m = Y.shape[0]
    a = np.ones(n) / n
    b = np.ones(m) / m

    C_xy = pairwise_distances(X, Y, metric='euclidean')
    C_xx = pairwise_distances(X, X, metric='euclidean')
    C_yy = pairwise_distances(Y, Y, metric='euclidean')

    ot_xy = ot.sinkhorn2(a, b, C_xy, reg)
    ot_xx = ot.sinkhorn2(a, a, C_xx, reg)
    ot_yy = ot.sinkhorn2(b, b, C_yy, reg)

    return 2 * ot_xy - ot_xx - ot_yy
