import numpy as np

import torch

from ignite.engine import Engine

from monaistream.streamrunners.streamrunner import StreamRunner
from monaistream.streamrunners.adaptors import StreamingDataLoader, IgniteEngineAdaptor
from monaistream.streamrunners.gstreamer.subnet import GstStreamRunnerSubnet
from monaistream.streamrunners.gstreamer.utils import run_pipeline, PadEntry, SubnetEntry



class DummyModel:
    def __init__(self):
        self._rng = torch.Generator()
        self._rng.manual_seed(12345678)


    def __call__(self, engine, batch):
        # do a bit of work
        print("DummyModel: __call__")
        for i in range(10):
            data = torch.rand(batch[0].shape, generator=self._rng) * 2 - 1
            batch[0] = batch[0] * data
        return batch


if __name__ == "__main__":
    engine = Engine(DummyModel())
    adaptor = IgniteEngineAdaptor(engine)

    input_configs = [
        PadEntry("sink_0", "video/x-raw,format=BGR,width=256,height=256"),
    ]

    output_configs = [
        PadEntry("src_0", "video/x-raw,format=BGR,width=256,height=256"),
    ]

    subnet_inputs = [
        SubnetEntry("sink_0", "videotestsrc pattern=0 ! video/x-raw,format=BGR,width=256,height=256 ! queue"),
    ]

    subnet_outputs = [
        SubnetEntry("src_0", "queue ! fakesink"),
    ]

    queue_config = None

    runner = StreamRunner(input_configs,
                          output_configs,
                          queue_config,
                          backend="gstreamer",
                          array_type="torch",
                          do_op=adaptor)

    subnet = GstStreamRunnerSubnet(runner,
                                   subnet_inputs,
                                   subnet_outputs)

    # subnet.run()
    run_pipeline(subnet.pipeline)
