r"""
A tour of blur operators
===================================================

This example provides a tour of 2D blur operators in DeepInv.
In particular, we show how to use DiffractionBlurs (Fresnel diffraction), motion blurs and space varying blurs.

"""

# %%
from deepinv.utils.demo import load_url_image, get_image_url
from deepinv.utils.plotting import plot
import deepinv as dinv
import torch
from deepinv.physics.generator import MotionBlurGenerator
from deepinv.physics.generator import DiffractionBlurGenerator
from deepinv.physics.generator import GeneratorMixture

from deepinv.physics.generator import ProductConvolutionPatchBlurGenerator
from deepinv.physics.generator import (
    DiffractionBlurGenerator,
    ProductConvolutionBlurGenerator,
    ProductConvolutionPatchBlurGenerator,
)
from deepinv.physics.blur import SpaceVaryingBlur
from deepinv.physics.functional.product_convolution import compute_patch_info

# %%
# Load test images
# ----------------
#
# First, let's load some test images.

dtype = torch.float32
device = "cpu"
img_size = (173, 125)

url = get_image_url("CBSD_0010.png")
x_rgb = load_url_image(
    url, grayscale=False, device=device, dtype=dtype, img_size=img_size
)

url = get_image_url("barbara.jpeg")
x_gray = load_url_image(
    url, grayscale=True, device=device, dtype=dtype, img_size=img_size
)

# Next, set the global random seed from pytorch to ensure reproducibility of the example.
torch.manual_seed(0)
torch.cuda.manual_seed(0)

# %%
# We are now ready to explore the different blur operators.
#
# Convolution Basics
# ------------------
#
# The class :class:`deepinv.physics.Blur` implements convolution operations with kernels.
#
# For instance, here is the convolution of a grayscale image with a grayscale filter:
filter_0 = dinv.physics.blur.gaussian_blur(sigma=(2, 0.1), angle=0.0)
physics = dinv.physics.Blur(filter_0, device=device)
y = physics(x_gray)
plot(
    [x_gray, filter_0, y],
    titles=["signal", "filter", "measurement"],
    suptitle="Grayscale convolution",
)

# %%
# When a single channel filter is used, all channels are convolved with the same filter:
#

physics = dinv.physics.Blur(filter_0, device=device)
y = physics(x_rgb)
plot(
    [x_rgb, filter_0, y],
    titles=["signal", "filter", "measurement"],
    suptitle="RGB image + grayscale filter convolution",
)

# %%
# By default, the boundary conditions are ``'valid'``, but other options among (``'circular'``, ``'reflect'``, ``'replicate'``) are possible:
#

physics = dinv.physics.Blur(filter_0, padding="reflect", device=device)
y = physics(x_rgb)
plot(
    [x_rgb, filter_0, y],
    titles=["signal", "filter", "measurement"],
    suptitle="Reflection boundary conditions",
)

# %%
# For circular boundary conditions, an FFT implementation is also available. It is slower that :meth:`deepinv.physics.Blur`,
# but inherits from :meth:`deepinv.physics.DecomposablePhysics`, so that the pseudo-inverse and regularized inverse are computed faster and more accurately.
#
physics = dinv.physics.BlurFFT(img_size=x_rgb[0].shape, filter=filter_0, device=device)
y = physics(x_rgb)
plot(
    [x_rgb, filter_0, y],
    titles=["signal", "filter", "measurement"],
    suptitle="FFT convolution with circular boundary conditions",
)

# %%
# One can also change the blur filter in the forward pass as follows:
filter_90 = dinv.physics.blur.gaussian_blur(sigma=(2, 0.1), angle=90.0).to(
    device=device, dtype=dtype
)
y = physics(x_rgb, filter=filter_90)
plot(
    [x_rgb, filter_90, y],
    titles=["signal", "filter", "measurement"],
    suptitle="Changing the filter on the fly",
)

# %%
# When applied to a new image, the last filter is used:
y = physics(x_gray, filter=filter_90)
plot(
    [x_gray, filter_90, y],
    titles=["signal", "filter", "measurement"],
    suptitle="Effect of on the fly change is persistent",
)

# %%
# We can also define color filters. In that situation, each channel is convolved with the corresponding channel of the filter:
psf_size = 9
filter_rgb = torch.zeros((1, 3, psf_size, psf_size), device=device, dtype=dtype)
filter_rgb[:, 0, :, psf_size // 2 : psf_size // 2 + 1] = 1.0 / psf_size
filter_rgb[:, 1, psf_size // 2 : psf_size // 2 + 1, :] = 1.0 / psf_size
filter_rgb[:, 2, ...] = (
    torch.diag(torch.ones(psf_size, device=device, dtype=dtype)) / psf_size
)
y = physics(x_rgb, filter=filter_rgb)
plot(
    [x_rgb, filter_rgb, y],
    titles=["signal", "Colour filter", "measurement"],
    suptitle="Color image + color filter convolution",
)

# %%
# Blur generators
# ----------------------
# More advanced kernel generation methods are provided with the toolbox thanks to
# the  :class:`deepinv.physics.generator.PSFGenerator`. In particular, motion blurs generators are implemented.

# %%
# Motion blur generators
# ~~~~~~~~~~~~~~~~~~~~~~

# %%
# In order to generate motion blur kernels, we just need to instantiate a generator with specific the psf size.
# In turn, motion blurs can be generated on the fly by calling the ``step()`` method. Let's illustrate this now and
# generate 3 motion blurs. First, we instantiate the generator:
#
psf_size = 31
motion_generator = MotionBlurGenerator((psf_size, psf_size), device=device, dtype=dtype)
# %%
# To generate new filters, we call the step() function:
filters = motion_generator.step(batch_size=3)
# the `step()` function returns a dictionary:
print(filters.keys())
plot(
    [f for f in filters["filter"]],
    suptitle="Examples of randomly generated motion blurs",
)

# %%
# Other options, such as the regularity and length of the blur trajectory can also be specified:
motion_generator = MotionBlurGenerator(
    (psf_size, psf_size), l=0.6, sigma=1, device=device, dtype=dtype
)
filters = motion_generator.step(batch_size=3)
plot([f for f in filters["filter"]], suptitle="Different length and regularity")

# %%
# Diffraction blur generators
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# We also implemented diffraction blurs obtained through Fresnel theory and definition of the psf through the pupil
# plane expanded in Zernike polynomials


diffraction_generator = DiffractionBlurGenerator(
    (psf_size, psf_size), device=device, dtype=dtype
)

# %%
# Then, to generate new filters, it suffices to call the step() function as follows:

filters = diffraction_generator.step(batch_size=3)

# %%
# In this case, the `step()` function returns a dictionary containing the filters,
# their pupil function and Zernike coefficients:
print(filters.keys())

# Note that we use **0.2 to increase the image dynamics
plot(
    [f for f in filters["filter"] ** 0.5],
    suptitle="Examples of randomly generated diffraction blurs",
)
plot(
    [
        f
        for f in torch.angle(filters["pupil"][:, None])
        * torch.abs(filters["pupil"][:, None])
    ],
    suptitle="Corresponding pupil phases",
)
print("Coefficients of the decomposition on Zernike polynomials")
print(filters["coeff"])

# %%
# We can change the cutoff frequency (below 1/4 to respect Shannon's sampling theorem)
diffraction_generator = DiffractionBlurGenerator(
    (psf_size, psf_size), fc=1 / 8, device=device, dtype=dtype
)
filters = diffraction_generator.step(batch_size=3)
plot(
    [f for f in filters["filter"] ** 0.5],
    suptitle="A different cutoff frequency",
)

# %%
# It is also possible to directly specify the Zernike decomposition.
# For instance, if the pupil is null, the PSF is the Airy pattern
n_zernike = len(
    diffraction_generator.list_param
)  # number of Zernike coefficients in the decomposition
filters = diffraction_generator.step(coeff=torch.zeros(3, n_zernike))
plot(
    [f for f in filters["filter"][:, None] ** 0.3],
    suptitle="Airy pattern",
)

# %%
# Finally, notice that you can activate the aberrations you want in the ANSI
# nomenclature https://en.wikipedia.org/wiki/Zernike_polynomials#OSA/ANSI_standard_indices
diffraction_generator = DiffractionBlurGenerator(
    (psf_size, psf_size), fc=1 / 8, list_param=["Z5", "Z6"], device=device, dtype=dtype
)
filters = diffraction_generator.step(batch_size=3)
plot(
    [f for f in filters["filter"] ** 0.5],
    suptitle="PSF obtained with astigmatism only",
)

# %%
# Generator Mixture
# ~~~~~~~~~~~~~~~~~
#
# During training, it's more robust to train on multiple family of operators. This can be done
# seamlessly with the :class:`deepinv.physics.generator.GeneratorMixture`.


torch.cuda.manual_seed(4)
torch.manual_seed(6)

generator = GeneratorMixture(
    ([motion_generator, diffraction_generator]), probs=[0.5, 0.5]
)
for i in range(4):
    filters = generator.step(batch_size=3)
    plot(
        [f for f in filters["filter"]],
        suptitle=f"Random PSF generated at step {i + 1}",
    )

# %%
# Space varying blurs
# --------------------
#
# Space varying blurs are also available using :class:`deepinv.physics.SpaceVaryingBlur`


psf_size = 32
img_size = (256, 256)
n_eigenpsf = 10
spacing = (64, 64)
padding = "valid"
batch_size = 1
delta = 16

# We first instantiate a psf generator
psf_generator = DiffractionBlurGenerator(
    (psf_size, psf_size), device=device, dtype=dtype
)
# Now, scattered random psfs are synthesized and interpolated spatially
pc_generator = ProductConvolutionBlurGenerator(
    psf_generator=psf_generator,
    img_size=img_size,
    n_eigen_psf=n_eigenpsf,
    spacing=spacing,
    padding=padding,
)
params_pc = pc_generator.step(batch_size)

physics = SpaceVaryingBlur(method="product_convolution2d", **params_pc)

dirac_comb = torch.zeros(img_size)[None, None]
dirac_comb[0, 0, ::delta, ::delta] = 1
psf_grid = physics(dirac_comb)
plot(psf_grid, titles="Space varying impulse responses")

num_patches = 4
i = torch.randint(
    0,
    img_size[0],
    (
        dirac_comb.size(0),
        num_patches,
    ),
)
j = torch.randint(
    0,
    img_size[1],
    (
        dirac_comb.size(0),
        num_patches,
    ),
)
centers = torch.stack((i, j), dim=-1)
psf = physics.get_psf(centers=centers)
plot(psf.flatten(0, 1))

# %%
img_size = 512
patch_size = 128
overlap = 64
psf_size = 31

psf_generator = DiffractionBlurGenerator(
    (psf_size, psf_size), device=device, dtype=dtype
)
patch_psf_generator = ProductConvolutionPatchBlurGenerator(
    psf_generator=psf_generator,
    image_size=img_size,
    patch_size=patch_size,
    overlap=overlap,
)
patch_info = {
    "patch_size": patch_size,
    "overlap": overlap,
    "num_patches": compute_patch_info(img_size, patch_size, overlap)["num_patches"],
}
params_pc = patch_psf_generator.step(batch_size)

patch_physics = SpaceVaryingBlur(
    method="product_convolution2d_patch", patch_info=patch_info, **params_pc
)

dirac_comb = torch.zeros(1, 1, img_size, img_size)
delta = 2 * psf_size
dirac_comb[0, 0, ::delta, ::delta] = 1

psf_grid = patch_physics(dirac_comb)
plot(psf_grid**0.1, titles="Space varying impulse responses")

# %%
num_patches = 4
i = torch.randint(
    patch_size,
    img_size - patch_size,
    (
        dirac_comb.size(0),
        num_patches,
    ),
)
j = torch.randint(
    patch_size,
    img_size - patch_size,
    (
        dirac_comb.size(0),
        num_patches,
    ),
)
centers = torch.stack((i, j), dim=-1)
psf = patch_physics.get_psf(centers=centers)
plot(psf.flatten(0, 1) ** 0.5)
# %%


def generate_random_patch(tensor, centers, patch_size: tuple[int]):
    """
    Args:
        tensor (Tensor): Tensor of patch_size (B, C, H, W) to be cropped.
        centers (Tensor): (B, num_patches, 2)
    Returns:
        Tensor: Randomly cropped Tensor of shape (num_patches, B, C, patch_size, patch_size)
    """
    if isinstance(patch_size, int):
        patch_size = (patch_size, patch_size)

    if centers.size(0) == 1:
        centers = centers.expand(tensor.size(0), -1, -1)
    centers[..., 0].clamp_(patch_size[0] // 2, tensor.size(-2) - patch_size[0] // 2)
    centers[..., 1].clamp_(patch_size[1] // 2, tensor.size(-1) - patch_size[1] // 2)
    random_patch = []

    for b in range(tensor.size(0)):
        for k in range(centers.size(1)):
            position = centers[b, k, :]
            ih, iw = patch_size[0] % 2, patch_size[1] % 2
            random_patch.append(
                tensor[
                    b : b + 1,
                    :,
                    position[0]
                    - patch_size[0] // 2 : position[0]
                    + patch_size[0] // 2
                    + ih,
                    position[1]
                    - patch_size[1] // 2 : position[1]
                    + patch_size[1] // 2
                    + iw,
                ]
            )
    return torch.stack(random_patch, dim=0)


centers = torch.stack(
    (torch.arange(0, img_size, delta), torch.arange(0, img_size, delta)), dim=1
)[None, 1:-1, :]
psf_grid_padded = torch.nn.functional.pad(
    psf_grid,
    (psf_size // 2, psf_size // 2, psf_size // 2, psf_size // 2),
    mode="constant",
    value=0,
)

psf = patch_physics.get_psf(centers)
plot(psf.flatten(0, 1) ** 0.5)

psf_hat = generate_random_patch(psf_grid_padded, centers, patch_size=psf_size)
plot(psf_hat.flatten(0, 1) ** 0.5)
plot((psf_hat - psf).flatten(0, 1) ** 0.5)

# %%
