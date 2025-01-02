import torch
from typing import List, Tuple
from deepinv.physics.generator import PhysicsGenerator
from deepinv.physics.blur import gaussian_blur, bilinear_filter, bicubic_filter


class DownSamplingGenerator(PhysicsGenerator):
    r"""
    Random downsampling generator.

    TODO: docstring
    """

    def __init__(
        self,
        filters: [str, List[str]] = ['gaussian', 'bilinear', 'bicubic'],
        factors: [int, List[int]] = [2, 4],
        rng: torch.Generator = None,
        device: str = "cpu",
        dtype: type = torch.float32,
    ) -> None:
        if isinstance(filters, str):
            filters = [filters]
        if isinstance(factors, int):
            factors = [factors]
        kwargs = {
            "list_filters": filters,
            "list_factors": factors,
        }
        super().__init__(
            device=device,
            dtype=dtype,
            rng=rng,
            **kwargs
        )

    def str2filter(self, filter_name: str, factor: int):
        if filter_name == "gaussian":
            filter = torch.nn.Parameter(
                gaussian_blur(sigma=(factor, factor)), requires_grad=False
            ).to(self.device)
        elif filter_name == "bilinear":
            filter = torch.nn.Parameter(
                bilinear_filter(factor), requires_grad=False
            ).to(self.device)
        elif filter_name == "bicubic":
            filter = torch.nn.Parameter(
                bicubic_filter(factor), requires_grad=False
            ).to(self.device)
        return filter

    def get_kernel(self, filter_str: str = None, factor=None):
        r"""
        TODO: docstring
        """
        batched_kernels = self.str2filter(filter_str, factor)
        return batched_kernels

    def step(
        self,
        batch_size: int = 1,
        seed: int = None,
    ):
        r"""
        TODO: docstring
        """
        self.rng_manual_seed(seed)

        random_indices = torch.randint(
            low=0,
            high=len(self.list_factors),
            size=(2,),
            generator=self.rng,
            **self.factory_kwargs
        )
        factor = self.list_factors[int(random_indices[0].item())]
        filter_str = self.list_filters[int(random_indices[1].item())]
        filters = self.get_kernel(filter_str, factor)
        return {
            "filter": filters,
            "factor": factor,
        }


