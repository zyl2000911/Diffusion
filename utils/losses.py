

import numpy as np

import torch as th




def compute_loss(model, D, inputs):
    inputs.requires_grad_(True)
    u_hat = model(inputs)
    u_hat_grad = th.autograd.grad(u_hat.sum(), inputs, create_graph=True)[0]
    du_hat_dt = u_hat_grad[:, 2]
    du_hat_dx2 = th.autograd.grad(u_hat_grad[:, 0].sum(), inputs, create_graph=True)[0][:, 0]  # 空间x的二次导数
    du_hat_dy2 = th.autograd.grad(u_hat_grad[:, 1].sum(), inputs, create_graph=True)[0][:, 1]  # 空间y的二次导数
    diff_eq = du_hat_dt - D * (du_hat_dx2 + du_hat_dy2)
    loss = (diff_eq ** 2).mean()
    return loss
def normal_kl(mean1, logvar1, mean2, logvar2, model, D, inputs):

    tensor = None
    for obj in (mean1, logvar1, mean2, logvar2):
        if isinstance(obj, th.Tensor):
            tensor = obj
            break
    assert tensor is not None, "at least one argument must be a Tensor"

    # Force variances to be Tensors. Broadcasting helps convert scalars to
    # Tensors, but it does not work for th.exp().
    logvar1, logvar2 = [
        x if isinstance(x, th.Tensor) else th.tensor(x).to(tensor)
        for x in (logvar1, logvar2)
    ]

    return 0.5 * logvar2 + 0.5 * logvar1 + compute_loss(model, D, inputs)



def approx_standard_normal_cdf(x):

    return 0.5 * (1.0 + th.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * th.pow(x, 3))))


def discretized_gaussian_log_likelihood(x, *, means, log_scales):

    assert x.shape == means.shape == log_scales.shape
    centered_x = x - means
    inv_stdv = th.exp(-log_scales)
    plus_in = inv_stdv * (centered_x + 1.0 / 255.0)
    cdf_plus = approx_standard_normal_cdf(plus_in)
    min_in = inv_stdv * (centered_x - 1.0 / 255.0)
    cdf_min = approx_standard_normal_cdf(min_in)
    log_cdf_plus = th.log(cdf_plus.clamp(min=1e-12))
    log_one_minus_cdf_min = th.log((1.0 - cdf_min).clamp(min=1e-12))
    cdf_delta = cdf_plus - cdf_min
    log_probs = th.where(
        x < -0.999,
        log_cdf_plus,
        th.where(x > 0.999, log_one_minus_cdf_min, th.log(cdf_delta.clamp(min=1e-12))),
    )
    assert log_probs.shape == x.shape
    return log_probs
