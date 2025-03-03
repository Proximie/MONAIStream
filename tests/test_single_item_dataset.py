
import unittest
import torch

from monai.utils import first

from monaistream.datasets.gstreamer import SingleItemDataset


class TestSingleItemDataset(unittest.TestCase):
    def setUp(self):
        self.rand_input = torch.rand(1, 3, 3)

    def test_single_input(self):
        ds = SingleItemDataset()
        ds.set_payload(self.rand_input)
        out = first(ds)

        self.assertEqual(out.shape, (1,) + tuple(self.rand_input.shape))

    def test_list_input(self):
        ds = SingleItemDataset()
        ds.set_payload([self.rand_input] * 2)
        out = first(ds)

        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].shape, (1,) + tuple(self.rand_input.shape))
        self.assertEqual(out[1].shape, (1,) + tuple(self.rand_input.shape))
