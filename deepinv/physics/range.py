import numpy as np
import torch
from deepinv.physics.forward import DecomposablePhysics


class Decolorize(DecomposablePhysics):
    r"""
    Converts RGB images to grayscale.

    Follows the `rec601 <https://en.wikipedia.org/wiki/Rec._601>`_ convention.

    Images must be tensors with 3 colour (RGB) channels, i.e. [*,3,*,*]
    The measurements are grayscale images.

    |sep|

    :Examples:

        Decolorize a 3x3 image:

        >>> from deepinv.physics import Decolorize
        >>> x = torch.ones(1, 3, 3, 3) # Define constant 3x3 RGB image
        >>> physics = Decolorize()
        >>> physics(x)
        tensor([[[[1.0000, 1.0000, 1.0000],
                  [1.0000, 1.0000, 1.0000],
                  [1.0000, 1.0000, 1.0000]]]], grad_fn=<MulBackward0>)
    """

    def __init__(self, channels=3, srf="rec601", **kwargs):
        super().__init__(**kwargs)
        if srf is None or srf == "rec601":
            self.srf = [0.4472 * 0.66851, 0.8781 * 0.66851, 0.1706 * 0.66851]
        elif srf in ("average", "flat"):
            self.srf = [1 / channels] * channels
        elif srf == "learn":
            raise NotImplementedError()  # TODO
        elif isinstance(srf, (tuple, list)):
            self.srf = srf
        else:
            raise ValueError("Invalid srf")

        if len(self.srf) < channels:
            # pad with zeros
            self.srf += [0] * (channels - len(self.srf))
        elif len(self.srf) > channels:
            raise ValueError("srf should be of length equal to or less than channels.")

        assert np.allclose(sum(self.srf), 1.0, rtol=1e-4)

        self.srf = torch.tensor(self.srf)

    def V_adjoint(self, x):
        if x.shape[1] != len(self.srf):
            raise ValueError("x should have same number of channels as SRF.")

        y = x * self.srf.view(1, len(self.srf), 1, 1)
        return torch.sum(y, dim=1, keepdim=True)

    def V(self, y):
        if y.shape[1] != 1:
            raise ValueError(
                "y should be grayscale i.e. have length 1 in the 1st dimension."
            )

        return y.expand(y.shape[0], len(self.srf), *y.shape[2:]) * self.srf.view(
            1, len(self.srf), 1, 1
        )


# # test code
# if __name__ == "__main__":
#    device = "cuda:0"
#    import deepinv as dinv
#    device = "cpu"
#    x = torch.randn((1, 3, 32, 32), device=device)
#    physics = Decolorize(device=device)
#    y = physics(x)
#    print(physics.adjointness_test(x))
#    print(physics.compute_norm(x))
#    xhat = physics.A_adjoint(y)
#    dinv.utils.plot([x, xhat, y])
