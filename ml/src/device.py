"""Central device selection for the ContractIQ ML layer.

Single source of truth so every module picks the same device:

    from .device import get_device
    device = get_device()

CUDA is used automatically when available; CPU remains a fully supported
fallback so the project runs unchanged on laptops without a GPU. Nothing here
hard-codes GPU ids or CUDA install paths.
"""
from __future__ import annotations

import torch


def get_device(prefer: str | None = None) -> torch.device:
    """Return the best available torch.device ('cuda' unless unavailable).

    prefer: optional explicit override ("cpu" forces CPU; anything else
    still validates against availability).
    """
    if prefer == "cpu":
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def device_summary(device: torch.device) -> str:
    if device.type == "cuda":
        props = torch.cuda.get_device_properties(0)
        return (f"cuda ({props.name}, {props.total_memory / 1024**3:.1f} GB VRAM, "
                f"torch {torch.__version__}, cuda runtime {torch.version.cuda})")
    return f"cpu (torch {torch.__version__})"
