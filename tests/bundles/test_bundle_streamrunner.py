import os
import unittest
from pathlib import Path
import monai.engines
import torch
import monai
from monai.bundle import ConfigWorkflow
from parameterized import parameterized

from monaistream.streamrunner.streamrunner import StreamRunner
from monaistream.streamrunner.adaptors import WorkflowEngineAdaptor
from monaistream.streamrunner.gstreamer.subnet import GstStreamRunnerSubnet
from monaistream.streamrunner.gstreamer.utils import run_pipeline, PadEntry, SubnetEntry

# in the MONAI image this causes an error because some import is already setting the start method
# torch.multiprocessing.set_start_method('spawn')

DEVICES = ["cpu"]
# if torch.cuda.is_available:
    # DEVICES.append("cuda:0")


class TestBundleStreamRunner(unittest.TestCase):
    def setUp(self):
        self.rand_input = torch.rand(1, 3, 5)
        self.test_dir=Path(__file__).resolve().parents[1]
        self.bundle_dir = self.test_dir / "test_bundles"
        self.endo_bundle = str(self.bundle_dir / "endoscopic_tool_segmentation")
        self.vid_2min = str(self.test_dir / "Case17_2min.mp4")

        # fileConfig(os.path.join(self.bundle_dir, "configs","logging.conf"))

    def test_bundles_present(self):
        self.assertTrue(os.path.isdir(self.endo_bundle), f"Failed to find {self.endo_bundle}, run init_bundles.sh")

    def test_bundle_load(self):
        cw = ConfigWorkflow(
            self.endo_bundle + "/configs/stream.json",
            self.endo_bundle + "/configs/metadata.json",
            workflow_type="infer",
        )
        cw.bundle_root = self.endo_bundle

        cw.initialize()
        result = cw.run()
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], monai.engines.Workflow)

    @parameterized.expand(DEVICES)
    def test_bundle_runner(self, device):

        cw = ConfigWorkflow(
            self.endo_bundle + "/configs/stream.json",
            self.endo_bundle + "/configs/metadata.json",
            workflow_type="infer",
        )
        cw.device = device
        cw.bundle_root = self.endo_bundle

        cw.initialize()
        (engine,) = cw.run()

        adaptor = WorkflowEngineAdaptor(engine)

        input_configs = [PadEntry("sink_0", "video/x-raw,format=RGB")]

        output_configs = [PadEntry("src_0", "video/x-raw,format=RGB")]

        subnet_inputs = [
            SubnetEntry(
                "sink_0",
                "videotestsrc pattern=0 num-buffers=1 ! video/x-raw,format=RGB,width=256,height=256 ! queue"
                # f"filesrc location={self.vid_2min} num-buffers=10 ! "
                # "qtdemux name=d d.video_0 ! decodebin ! videoconvert",
            )
        ]

        subnet_outputs = [SubnetEntry("src_0", "queue ! fakesink")]

        runner = StreamRunner(
            input_configs, output_configs, None, backend="gstreamer", array_type="torch", do_op=adaptor
        )

        subnet = GstStreamRunnerSubnet(runner, subnet_inputs, subnet_outputs)

        # subnet.run()
        run_pipeline(subnet.pipeline)
