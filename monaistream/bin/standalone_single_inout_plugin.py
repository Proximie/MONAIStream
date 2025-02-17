import argparse

import inspect

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
from gi.repository import Gst

import numpy as np
from monaistream.streamrunners.utils import run_pipeline
from monaistream.streamrunners.gstreamer_noplugin import create_registerable_plugin

Gst.init()
from monaistream.streamrunners.gstreamer_plugin import GstAdaptorStreamRunner

FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"


class MyAdaptorOp(GstAdaptorStreamRunner):

    def do_op(self, src_data, snk_data):
        print(f"got source data with shape {src_data.shape}")
        snk_data[...] = src_data[:snk_data.shape[0], :snk_data.shape[1], :]

# TDOO: the do_op function should not need to be passed self
def do_op(self, src_data, snk_data):
    print(f"got source data with shape {src_data.shape}")
    snk_data[...] = src_data[:snk_data.shape[0], :snk_data.shape[1], :]


if __name__ == '__main__':
    """
    TODO:
     - specify source/sink one of several ways:
       - pipeline descriptor string
       - presets that look up descriptor strings (with argument specification)
     - move runner class inside a factory class
       - the runner is constructed
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dynamic", help="Construct the stream runner dynamically", action="store_true")

    args = parser.parse_args()

    print(f"dynamic: {args.dynamic}")

    if args.dynamic:
        runner_type = create_registerable_plugin(GstAdaptorStreamRunner,
                                                 "DynamicAdaptorOp",
                                                 do_op)
    else:
        runner_type = MyAdaptorOp

    pipeline_descriptor = (
        'videotestsrc is-live=true '
        '! videoconvert '
        # '! myop message=foo '
        '! queue '
        '! myop '
        '! queue '
        '! videoconvert '
        '! fakesink'
    )
    print(pipeline_descriptor)

    run_pipeline(runner_type, "myop", pipeline_descriptor)
