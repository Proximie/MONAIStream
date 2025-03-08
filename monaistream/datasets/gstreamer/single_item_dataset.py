
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

