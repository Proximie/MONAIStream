# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import logging
import unittest
from typing import Any, Callable
from tempfile import TemporaryDirectory

import torch
from monai.handlers import MeanSquaredError, from_engine
from monai.bundle import ConfigWorkflow
from monai.utils import CommonKeys, first
from parameterized import parameterized

from monaistream.gstreamer import Gst, GstBase, GObject
from monaistream.gstreamer.utils import get_video_pad_template, map_buffer_to_tensor, get_buffer_tensor
from monaistream import SingleItemDataset, RingBufferDataset, StreamRunner
from monaistream.gstreamer.launch import default_loop_runner
from tests.utils import SkipIfNoModule


DEVICES = ["cpu"]
if torch.cuda.is_available:
    DEVICES.append("cuda:0")


class TensorCallbackTransform(GstBase.BaseTransform):
    __gstmetadata__ = ("Tensor Callback Transform", "Transform", "Description", "Author")  # TODO: correct info

    __gsttemplates__ = (
        get_video_pad_template("src", Gst.PadDirection.SRC),
        get_video_pad_template("sink", Gst.PadDirection.SINK),
    )

    def __init__(self, trans_fn: Callable | None = None):
        super().__init__()
        self.trans_fn = trans_fn
        self.device = "cpu"

    def do_transform(self, inbuf: Gst.Buffer, outbuf: Gst.Buffer) -> Gst.FlowReturn:
        intensor = get_buffer_tensor(inbuf, self.srcpad.get_current_caps(), device=self.device)
        with map_buffer_to_tensor(outbuf, Gst.MapFlags.WRITE, self.sinkpad.get_current_caps()) as outtensor:
            outtensor[:] = self.trans_fn(intensor)

        return Gst.FlowReturn.OK


class TestSingleItemDataset(unittest.TestCase):
    def setUp(self):
        self.rand_input = torch.rand(1, 3, 3)

    def test_single_input(self):
        ds = SingleItemDataset()
        ds.set_item(self.rand_input)
        out = first(ds)

        self.assertEqual(out.shape, (1,) + tuple(self.rand_input.shape))

    def test_list_input(self):
        ds = SingleItemDataset()
        ds.set_item([self.rand_input] * 2)
        out = first(ds)

        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].shape, (1,) + tuple(self.rand_input.shape))
        self.assertEqual(out[1].shape, (1,) + tuple(self.rand_input.shape))


class TestRingBufferDataset(unittest.TestCase):
    def setUp(self):
        self.rand_input = torch.rand(1, 3, 3)

    def test_single_input(self):
        ds = RingBufferDataset(5)
        ds.set_item(self.rand_input)

        out = first(ds)

        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 5)

        for i in out:
            self.assertEqual(i.shape, (1,) + tuple(self.rand_input.shape))


@SkipIfNoModule("ignite")
class TestStreamRunner(unittest.TestCase):
    def setUp(self):
        self.rand_input = torch.rand(1, 3, 5)
        self.bundle_dir = os.path.dirname(__file__) + "/test_bundles/blur"
        # fileConfig(os.path.join(self.bundle_dir, "configs","logging.conf"))

    @parameterized.expand(DEVICES)
    def test_single_input(self, device):
        net = torch.nn.Identity()
        engine = StreamRunner(network=net, device=device, use_interrupt=False)

        result = engine(self.rand_input)

        self.assertIsInstance(result, torch.Tensor)
        self.assertEqual(result.shape, self.rand_input.shape)
        self.assertEqual(result.device, torch.device(device))

    @parameterized.expand(DEVICES)
    def test_two_inputs(self, device):
        net = torch.nn.Identity()
        engine = StreamRunner(network=net, device=device, use_interrupt=False)

        result1 = engine(self.rand_input.to(device))
        result2 = engine(self.rand_input.to(device))

        self.assertIsInstance(result1, torch.Tensor)
        self.assertIsInstance(result2, torch.Tensor)

        self.assertEqual(result1.shape, self.rand_input.shape)
        self.assertEqual(result2.shape, self.rand_input.shape)

        self.assertEqual(engine.state.iteration, 1)

    @parameterized.expand(DEVICES)
    def test_ring_buffer(self, device):
        from monai.engines.utils import default_prepare_batch, PrepareBatch

        class TuplePrepareBatch(PrepareBatch):
            def __call__(
                self,
                batchdata: dict[str, torch.Tensor],
                device: str | torch.device | None = None,
                non_blocking: bool = False,
                **kwargs: Any,
            ) -> Any:
                assert isinstance(batchdata, tuple)
                batches=[default_prepare_batch(b, device, non_blocking, **kwargs) for b in batchdata]
                if isinstance(batches[0], tuple) and len(batches[0])==2:
                    inputs,outputs=zip(*batches)
                else:
                    inputs=tuple(batches)
                    outputs=(None,)*len(inputs)

                return tuple(inputs),tuple(outputs)

        class FakeMultiInputNet(torch.nn.Module):
            def forward(self,x):
                assert isinstance(x, tuple)
                assert isinstance(x[0], torch.Tensor), type(x[0])
                return torch.as_tensor([i.mean() for i in x])

        with self.subTest("Identity Net"):
            engine = StreamRunner(
                data_loader=RingBufferDataset(5),
                prepare_batch=TuplePrepareBatch(),
                network=torch.nn.Identity(),
                device=device,
                use_interrupt=False,
            )

            result = engine(self.rand_input)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 5)

            for r,_ in result:
                self.assertIsInstance(r, torch.Tensor)
                self.assertEqual(r.shape, self.rand_input.shape)
                self.assertEqual(r.device, torch.device(device))

        with self.subTest("MultiInput Net"):
            engine = StreamRunner(
                data_loader=RingBufferDataset(5),
                prepare_batch=TuplePrepareBatch(),
                network=FakeMultiInputNet(),
                device=device,
                use_interrupt=False,
            )

            result = engine(self.rand_input)

            self.assertIsInstance(result, torch.Tensor)
            self.assertEqual(result.shape,(1,5))

    @parameterized.expand(DEVICES)
    def test_metric(self, device):
        net = torch.nn.Identity()
        metric = MeanSquaredError(output_transform=from_engine([CommonKeys.IMAGE, CommonKeys.PRED]))
        engine = StreamRunner(network=net, device=device, key_val_metric={"mse": metric}, use_interrupt=False)

        result, mets = engine(self.rand_input.to(device), include_metrics=True)

        self.assertIsInstance(result, torch.Tensor)
        self.assertEqual(result.shape, self.rand_input.shape)
        self.assertIsInstance(mets, dict)
        self.assertIn("mse", mets)
        self.assertEqual(mets["mse"], 0)

    @parameterized.expand(DEVICES)
    def test_bundle_stream(self, device):
        bw = ConfigWorkflow(
            self.bundle_dir + "/configs/stream.json", self.bundle_dir + "/configs/metadata.json", workflow_type="infer"
        )
        bw.device = device

        bw.initialize()
        cb = bw.run()
        self.assertEqual(len(cb), 1)
        self.assertIsInstance(cb[0], StreamRunner)

        with TemporaryDirectory() as td:
            RunnerType = GObject.type_register(TensorCallbackTransform)
            Gst.Element.register(None, "tensorcallbacktransform", Gst.Rank.NONE, RunnerType)
            img = os.path.join(td, "img.jpg")

            pipeline = Gst.parse_launch(
                f"videotestsrc num-buffers=1 ! tensorcallbacktransform name=t ! jpegenc ! filesink location={img}"
            )

            tcbt = pipeline.get_by_name("t")
            tcbt.device = device
            tcbt.trans_fn = cb[0]

            default_loop_runner(pipeline, None)
            self.assertTrue(os.path.isfile(img))


if __name__ == "__main__":
    unittest.main()
