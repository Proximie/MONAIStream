import inspect

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
from gi.repository import Gst, GLib, GObject, GstBase

import numpy as np

Gst.init()
from monaistream.streamrunners.gstreamer_plugin import (
    GstMultiInputStreamRunner,
    GstMultiInputStreamRunner2,
    GstMultiInputStreamRunner3,
    GstMultiInOutStreamRunner2,
    GstMultiInOutStreamRunner2_5,
    GstMultiInOutStreamRunner3,
)

FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"


class MyAdaptorOp(GstMultiInputStreamRunner):

    def do_op(self, input_data):
        print(f"got input data with shapes {[input_data[i].shape for i in range(len(input_data))]}")
        output_data = np.array(input_data[0])
        output_data[:128, :128, :] = input_data[1]
        return output_data


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
    # pipeline_descriptor = (
    # "videotestsrc pattern=0 ! video/x-raw, width=256, height=256, format=RGB ! queue ! myop.sink_0 "
    # "videotestsrc pattern=1 ! video/x-raw, width=128, height=128, format=RGB ! queue ! myop.sink_1 "
    # "myop ! videoconvert ! fakesink"
    # )
    pipeline_descriptor = (
        "myop name=myop " 
        "videotestsrc pattern=0 ! video/x-raw, width=256, height=256, format=RGB ! queue ! myop. "
        "videotestsrc pattern=1 ! video/x-raw, width=128, height=128, format=RGB ! queue ! myop. "
        "myop ! queue ! videoconvert ! fakesink"
    )

    # pipeline_descriptor = (
    #     "videotestsrc pattern=0 ! video/x-raw,width=256,height=256 ! myop.sink_1 "
    #     "videotestsrc pattern=1 ! video/x-raw,width=128,height=128 ! myop.sink_2 "
    #     "myop. "
    #     "tee name=t ! queue ! videoconvert ! fakesink t. ! queue ! videoconvert ! fakesink"
    # )
    # pipeline_descriptor = (
    #     "myop name=myop "
    #     "videotestsrc pattern=0 ! video/x-raw,width=256,height=256 ! myop.sink_1 "
    #     "videotestsrc pattern=1 ! video/x-raw,width=128,height=128 ! myop.sink_2 "
    #     "myop.src_1 ! queue ! videoconvert ! fakesink "
    #     "myop.src_2 ! queue ! videoconvert ! fakesink"
    # )
    print(pipeline_descriptor)

    run_pipeline(pipeline_descriptor)
