import numpy as np
import gi
import traceback
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

n = 0
def process_frame(processor_id, app_src):
    def _inner(sink):
        """Callback function to process each video frame."""
        global n
        print(f"frame {n} for processor_id {processor_id}")
        n += 1

        sample = sink.emit("pull-sample")
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
        app_src.emit("push-buffer", new_buffer)

        return Gst.FlowReturn.OK
    
    return _inner


# Create pipeline
pipeline_in_0 = Gst.parse_launch(
    "videotestsrc is-live=true "
    "! videoconvert "
    "! video/x-raw,format=BGR "
    "! queue "
    "! appsink name=app_sink_0 "
)

pipeline_in_1 = Gst.parse_launch(
    "videotestsrc is-live=true "
    "! videoconvert "
    "! video/x-raw,format=BGR "
    "! queue "
    "! appsink name=app_sink_1 "
)

pipeline_out_0 = Gst.parse_launch(
    "appsrc name=mysrc "
    "! queue "
    "! videoconvert "
    "! x264enc "
    "! mp4mux "
    "! fakesink"
)

# Get elements
appsink_0 = pipeline_in_0.get_by_name("app_sink_0")
appsink_1 = pipeline_in_1.get_by_name("app_sink_1")
appsrc = pipeline_out_0.get_by_name("mysrc")

# Configure appsink_0
appsink_0.set_property("emit-signals", True)
appsink_0.set_property("max-buffers", 1)
appsink_0.set_property("drop", True)
appsink_0.connect("new-sample", process_frame(0, appsrc))

# Configure appsink_1
appsink_1.set_property("emit-signals", True)
appsink_1.set_property("max-buffers", 1)
appsink_1.set_property("drop", True)
appsink_1.connect("new-sample", process_frame(1, appsrc))

# Configure appsrc
caps = Gst.Caps.from_string("video/x-raw, format=BGR, width=640, height=480, framerate=30/1")
appsrc.set_property("caps", caps)
appsrc.set_property("format", Gst.Format.TIME)
appsrc.set_property("block", True)
appsrc.set_property("is-live", True)

# Start pipeline
pipeline_out_0.set_state(Gst.State.PLAYING)
pipeline_in_0.set_state(Gst.State.PLAYING)
pipeline_in_1.set_state(Gst.State.PLAYING)

# Run main loop
loop = GLib.MainLoop()
print("set up main loop")
try:
    loop.run()
except KeyboardInterrupt:
    raise
except Exception as e:
    print(f"Exiting due to: {traceback.format_exc()}")
finally:
    if loop and loop.is_running():
        loop.quit()
    if pipeline_in_0:
        pipeline_in_0.set_state(Gst.State.NULL)
    if pipeline_in_1:
        pipeline_in_1.set_state(Gst.State.NULL)
    if pipeline_out_0:
        pipeline_out_0.set_state(Gst.State.NULL)
    print("Pipeline stopped.")

# Stop pipeline
# pipeline.set_state(Gst.State.NULL)
