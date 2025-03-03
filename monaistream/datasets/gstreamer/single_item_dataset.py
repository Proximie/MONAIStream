
from typing import Callable, Sequence
import torch
from monai.data import Dataset


__all__ = ["SingleItemDataset"]


class SingleItemDataset(Dataset):
    """
    This simple dataset only ever has one item and acts as its own iterable so to avoid needing DataLoader.
    """

    def __init__(self, transform: Sequence[Callable] | Callable | None = None) -> None:
        super().__init__([None], transform)

    def set_payload(self, item):
        self.data[0] = item

    def __iter__(self):
        item = self[0]

        # TODO: use standard way of adding batch dimensions, or do something specific here
        # for how groups of frames would be passed?
        if isinstance(item, torch.Tensor):
            yield item[None]
        elif isinstance(item, Sequence):
            yield tuple(v[None] for v in item)
        else:
            yield {k: v[None] for k, v in item.items()}

