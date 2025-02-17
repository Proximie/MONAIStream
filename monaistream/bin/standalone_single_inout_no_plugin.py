import numpy as np
import gi
import traceback
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


Gst.init(None)


def stop_pipeline(pipeline0, pipeline1, loop):
    if loop and loop.is_running():
        print("Stopping loop")
        loop.quit()
    if pipeline0 and pipeline0.get_state(0)[1] == Gst.State.PLAYING:
        print("Stopping pipeline0")
        pipeline0.set_state(Gst.State.NULL)
    if pipeline0 and pipeline1.get_state(0)[1] == Gst.State.PLAYING:
        print("Stopping pipeline1")
        pipeline1.set_state(Gst.State.NULL)


def on_caps_change(pad, info, appsrc):
    """Callback to detect caps change on appsink and update appsrc caps."""
    print("on_caps_change")
    event = info.get_event()

    if event.type == Gst.EventType.CAPS:
        caps = event.parse_caps()
        if caps:
            print("Detected caps change on appsink:", caps.to_string())

            # Update the caps on appsrc
            appsrc.set_property("caps", caps)
            print("Updated appsrc caps to:", caps.to_string())

    return Gst.PadProbeReturn.OK


n = 0
def process_frame():
    n = 0

    def _inner(appsink, appsrc):
        """Callback function to process each video frame."""
        global n
        print(f"frame {n}")
        n += 1

        sample = appsink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.ERROR

        buffer = sample.get_buffer()
        caps = sample.get_caps()
        width = caps.get_structure(0).get_int("width")[1]
        height = caps.get_structure(0).get_int("height")[1]

        # Extract data from buffer
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.ERROR

        frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
        buffer.unmap(map_info)
        dframe = np.array(frame)
        # Blank out top-left corner (e.g., 100x100 pixels)
        dframe[:100, :100] = (0, 0, 0)  # Set pixels to black (BGR)

        # Push modified frame to appsrc
        new_buffer = Gst.Buffer.new_wrapped(dframe.tobytes())
        appsrc.emit("push-buffer", new_buffer)

        return Gst.FlowReturn.OK

    return _inner


# Create pipeline
pipeline = Gst.parse_launch(
    "videotestsrc is-live=true "
    "! videoconvert "
    "! video/x-raw,format=BGR "
    "! queue "
    "! appsink name=mysink "
)


pipeline2 = Gst.parse_launch(
    "appsrc name=mysrc "
    "! queue "
    "! videoconvert "
    "! x264enc "
    "! mp4mux "
    "! fakesink"
)


def build_pipeline_1():
    # Get elements
    appsink = pipeline.get_by_name("mysink")
    appsrc = pipeline2.get_by_name("mysrc")

    # Configure appsink
    appsink.set_property("emit-signals", True)
    appsink.set_property("max-buffers", 1)
    appsink.set_property("drop", True)
    appsink.connect("new-sample", process_frame(), appsrc)
    # appsink_pad = appsink.get_static_pad("sink")
    # appsink_pad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, on_caps_change, appsrc)

    # appsink_caps = appsink.get_caps()
    # print(appsink_caps.to_string())

    # Configure appsrc
    caps = Gst.Caps.from_string("video/x-raw, format=BGR, width=320, height=240, framerate=30/1")
    appsrc.set_property("caps", caps)

    # appsrc.set_property("caps", appsink_caps)

    appsrc.set_property("format", Gst.Format.TIME)
    appsrc.set_property("block", True)
    appsrc.set_property("is-live", True)

    return pipeline, pipeline2


def build_pipeline_1():
    # Get elements
    appsink = pipeline.get_by_name("mysink")
    appsrc = pipeline2.get_by_name("mysrc")

    # Configure appsink
    appsink.set_property("emit-signals", True)
    appsink.set_property("max-buffers", 1)
    appsink.set_property("drop", True)
    appsink.connect("new-sample", process_frame(), appsrc)
    appsink_pad = appsink.get_static_pad("sink")
    appsink_pad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, on_caps_change, appsrc)

    # appsink_caps = appsink.get_caps()
    # print(appsink_caps.to_string())

    # Configure appsrc
    caps = Gst.Caps.from_string("video/x-raw, format=BGR, width=320, height=240, framerate=30/1")
    appsrc.set_property("caps", caps)

    # appsrc.set_property("caps", appsink_caps)

    appsrc.set_property("format", Gst.Format.TIME)
    appsrc.set_property("block", True)
    appsrc.set_property("is-live", True)

    return pipeline, pipeline2


if __name__ == "__main__":
    pipeline0, pipeline1 = build_pipeline_1()
    # Start pipeline
    pipeline1.set_state(Gst.State.PLAYING)
    pipeline0.set_state(Gst.State.PLAYING)

    # Run main loop
    loop = GLib.MainLoop()
    GLib.timeout_add_seconds(5, stop_pipeline, pipeline0, pipeline1, loop)
    print("set up main loop")
    try:
        loop.run()
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"Exiting due to: {traceback.format_exc()}")
    finally:
        stop_pipeline(pipeline0, pipeline1, loop)
