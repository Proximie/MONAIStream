import argparse
import inspect

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
from gi.repository import Gst, GLib, GObject, GstBase

import numpy as np

from monaistream.streamrunners.gstreamer.utils import (
    create_registerable_plugin,
    register,
    run_pipeline
)


Gst.init()


from monaistream.streamrunners.gstreamer.backend import GstStreamRunnerBackend, GstStreamRunnerBackendStatic
from monaistream.streamrunners.gstreamer.utils import PadEntry


FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"


base_class = GstStreamRunnerBackend



class MyAdaptorOp(base_class):

    def __init__(self):
        inputs = (PadEntry("sink_0", "video/x-raw, format=BGR, width=256, height=256"),
                PadEntry("sink_1", "video/x-raw, format=BGR, width=128, height=128"))
        outputs = (PadEntry("src_0", "video/x-raw, format=BGR, width=256, height=256"),
                PadEntry("src_1", "video/x-raw, format=BGR, width=128, height=128"))
        super().__init__(inputs=inputs, outputs=outputs, do_op=do_op)



def do_op(input_data):
    print(f"got source data with shape {tuple(d.shape for d in input_data)}")
    return input_data



def construct_pipeline(runner):
    pipeline = Gst.Pipeline().new("pipeline")

    videotestsrc0 = Gst.ElementFactory.make("videotestsrc", "videotestsrc0")
    videotestsrc0.set_caps(Gst.Caps.from_string("video/x-raw,width=256,height=256"))
    prequeue0 = Gst.ElementFactory.make("queue", "prequeue0")

    videotestsrc1 = Gst.ElementFactory.make("videotestsrc", "videotestsrc1")
    videotestsrc1.set_caps(Gst.Caps.from_string("video/x-raw,width=128,height=128"))
    prequeue1 = Gst.ElementFactory.make("queue", "prequeue1")

    postqueue0 = Gst.ElementFactory.make("queue", "postqueue0")
    videoconvert0 = Gst.ElementFactory.make("videoconvert", "videoconvert0")
    fakesink0 = Gst.ElementFactory.make("fakesink", "fakesink0")

    postqueue1 = Gst.ElementFactory.make("queue", "postqueue1")
    videoconvert1 = Gst.ElementFactory.make("videoconvert", "videoconvert1")
    fakesink1 = Gst.ElementFactory.make("fakesink", "fakesink1")

    pipeline.add(videotestsrc0)
    pipeline.add(prequeue0)
    pipeline.add(videotestsrc1)
    pipeline.add(prequeue1)
    pipeline.add(runner)
    pipeline.add(postqueue0)
    pipeline.add(videoconvert0)
    pipeline.add(fakesink0)
    pipeline.add(postqueue1)
    pipeline.add(videoconvert1)
    pipeline.add(fakesink1)

    videotestsrc0.link(prequeue0)
    videotestsrc1.link(prequeue1)
    prequeue0.link_pads("src", runner, "sink_0")
    prequeue1.link_pads("src", runner, "sink_1")
    runner.link_pads("src_0", postqueue0)
    runner.link_pads("src_1", postqueue1)
    postqueue0.link(videoconvert0)
    videoconvert0.link(fakesink0)
    postqueue1.link(videoconvert1)
    videoconvert1.link(fakesink1)

    return pipeline



if __name__ == '__main__':
    """
    TODO:
     - specify source/sink one of several ways:
       - pipeline descriptor string
       - presets that look up descriptor strings (with argument specification)
     - move runner class inside a factory class
       - the runner is constructed
    """

    methods = ("inherit", "dynamic", "code")
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--method",
                        help="How to contruct the pipeline: {methods}", choices=methods)
    parser.add_argument("-c")

    args = parser.parse_args()

    pipeline_descriptor = (
        "myop name=myop "
        "videotestsrc pattern=0 ! video/x-raw,format=BGR,width=256,height=256 ! queue ! myop.sink_0 "
        "videotestsrc pattern=1 ! video/x-raw,format=BGR,width=128,height=128 ! queue ! myop.sink_1 "
        "myop.src_0 ! queue ! videoconvert ! fakesink "
        "myop.src_1 ! queue ! videoconvert ! fakesink"
    )

    inputs = (PadEntry("sink_0", "video/x-raw, format=BGR, width=256, height=256"),
              PadEntry("sink_1", "video/x-raw, format=BGR, width=128, height=128"))
    outputs = (PadEntry("src_0", "video/x-raw, format=BGR, width=256, height=256"),
               PadEntry("src_1", "video/x-raw, format=BGR, width=128, height=128"))

    if args.method != methods[2]:
        if args.method == methods[0]:
            runner_type = MyAdaptorOp
        else: # dynamic
            runner_type = create_registerable_plugin(base_class,
                                                    "DynamicAdaptorOp",
                                                    inputs,
                                                    outputs,
                                                    do_op)
        register(runner_type, "myop")
        pipeline = Gst.parse_launch(pipeline_descriptor)
        # run_pipeline(runner_type, "myop", pipeline_descriptor)
        run_pipeline(pipeline)
    else: # code
        runner = base_class(do_op=do_op)
        for i in inputs:
            runner.add_input(i.name, i.format)
        # runner.add_input("sink_0", f"video/x-raw, format=BGR, width=256, height=256")
        # runner.add_input("sink_1", f"video/x-raw, format=BGR, width=128, height=128")
        for o in outputs:
            runner.add_output(o.name, o.format)
        # runner.add_output("src_0", f"video/x-raw, format=BGR, width=256, height=256")
        # runner.add_output("src_1", f"video/x-raw, format=BGR, width=128, height=128")
        print("runner sink_pads:", runner.sinkpads)
        print("runner_src_pads:", runner.srcpads)
        pipeline = construct_pipeline(runner)
        run_pipeline(pipeline)
