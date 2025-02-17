import inspect

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
from gi.repository import Gst, GLib, GObject, GstBase

import numpy as np

Gst.init()
from monaistream.streamrunners.gstreamer_plugin import GstAdaptorStreamRunner

FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"


class MyAdaptorOp(GstAdaptorStreamRunner):

    def do_op(self, src_data, snk_data):
        print(f"got source data with shape {src_data.shape}")
        snk_data[...] = src_data[:snk_data.shape[0], :snk_data.shape[1], :]


def register(runner_type, runner_alias):
    RunnerType = GObject.type_register(runner_type)
    if not Gst.Element.register(None, runner_alias, Gst.Rank.NONE, RunnerType):
        raise RuntimeError(f"Failed to register {runner_alias}; you may be missing gst-python plugins")


def run_pipeline(pipeline_descriptor):

    # register(MyInPlaceOp, 'myop')
    register(MyAdaptorOp, 'myop')

    pipeline = Gst.parse_launch(pipeline_descriptor)

    pipeline.set_state(Gst.State.PLAYING)

    loop = GLib.MainLoop()
    try:
        print("running loop")
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    """
    TODO:
     - specify source/sink one of several ways:
       - pipeline descriptor string
       - presets that look up descriptor strings (with argument specification)
     - move runner class inside a factory class
       - the runner is constructed
    """



    # run_pipeline(
    #     'udpsrc address=0.0.0.0 port=5001 caps=application/x-rtp,media=video,payout=96,encoding-name=H264',
    #     'udpsink host=255.255.255.255 port=5002'
    # )
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

    run_pipeline(pipeline_descriptor)
