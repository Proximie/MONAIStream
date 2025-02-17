import sys
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

import numpy as np
import traceback
from gi.repository import Gst, GObject, GLib

from monaistream.streamrunners.utils import register

Gst.init(None)

n = 0
def process_frame(sink, appsrc):
    """Callback function to process each video frame."""
    print("process_frame")
    global n
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
    appsrc.emit("push-buffer", new_buffer)

    print(f"Processed frame {n}")
    n += 1

    return Gst.FlowReturn.OK


class MyProcessingBin(Gst.Bin):
    def __init__(self):
        super(MyProcessingBin, self).__init__()

        # Create elements
        self.appsink = Gst.ElementFactory.make("appsink", "mysink")
        self.appsink.set_property("emit-signals", True)
        self.appsink.set_property("max-buffers", 1)
        self.appsink.set_property("drop", True)
        self.appsink.connect("new-sample", process_frame)

        self.appsrc = Gst.ElementFactory.make("appsrc", "mysrc")
        self.appsrc.set_property("caps", Gst.Caps.from_string("video/x-raw, format=BGR, width=640, height=480, framerate=30/1"))
        self.appsrc.set_property("format", Gst.Format.TIME)
        self.appsrc.set_property("block", True)
        self.appsrc.set_property("is-live", True)

        # Add elements to bin
        self.add(self.appsink)
        self.add(self.appsrc)

        # Create ghost pads to allow linking in pipeline
        sink_pad = self.appsink.get_static_pad("sink")
        if sink_pad:
            ghost_sink_pad = Gst.GhostPad.new("sink", sink_pad)
            self.add_pad(ghost_sink_pad)

        # Get the dynamically created source pad from appsrc
        self.appsrc.set_state(Gst.State.READY)  # Ensure the pad is available
        src_pad = self.appsrc.get_static_pad("src")
        if not src_pad:
            src_pad = self.appsrc.get_pad("src")  # Use get_pad() for dynamic pads
        if src_pad:
            ghost_src_pad = Gst.GhostPad.new("src", src_pad)
            self.add_pad(ghost_src_pad)


class MyProcessingBin2(Gst.Bin):
    def __init__(self):
        super(MyProcessingBin2, self).__init__()

        # Create elements
        self.appsink = Gst.ElementFactory.make("appsink", "mysink")
        self.appsink.set_property("emit-signals", True)
        self.appsink.set_property("max-buffers", 1)
        self.appsink.set_property("drop", True)

        self.appsrc = Gst.ElementFactory.make("appsrc", "mysrc")
        self.appsrc.set_property("caps", Gst.Caps.from_string("video/x-raw, format=BGR, width=640, height=480, framerate=30/1"))
        self.appsrc.set_property("format", Gst.Format.TIME)
        self.appsrc.set_property("block", True)
        self.appsrc.set_property("is-live", True)

        # Connect process_frame
        self.appsink.connect("new-sample", process_frame, self.appsrc)

        # Add elements to bin
        self.add(self.appsink)
        self.add(self.appsrc)

        # for pad in self.appsink.pads:
        #     print("pad:", pad, pad.get_name(), pad.get_direction())
        # print("static_pad:", self.appsink.get_static_pad("sink"))
        # for pad in self.appsink.pads:
        #     print("pad:", pad, pad.get_name(), pad.get_direction())
        # print("static_pad:", self.appsink.get_static_pad("sink"))

        # Create ghost pads for external pipeline linking
        sink_pad = self.appsink.get_static_pad("sink")
        src_pad = self.appsrc.get_static_pad("src")

        print("sink_pad:", sink_pad)
        if sink_pad:
            ghost_sink_pad = Gst.GhostPad.new("sink", sink_pad)
            self.add_pad(ghost_sink_pad)
        else:
            print("Sink pad not found.")

        if src_pad:
            ghost_src_pad = Gst.GhostPad.new("src", src_pad)
            self.add_pad(ghost_src_pad)
        else:
            print("Source pad not found.")



class MyProcessingBin3(Gst.Bin):


    def __init__(self):
        super(MyProcessingBin3, self).__init__()

        print("Creating a new MyProcessingBin3")

        # Create appsink element
        self.appsink = Gst.ElementFactory.make('appsink', 'sink')
        self.appsink.set_property('emit-signals', True)  # Enable signal emitting to allow callbacks
        self.appsink.set_property('sync', False)  # Disable sync to process data as fast as possible

        # Create appsrc element
        self.appsrc = Gst.ElementFactory.make('appsrc', 'src')
        self.appsrc.set_property('is-live', True)  # Operate in live mode
        self.appsrc.set_property('format', Gst.Format.TIME)  # Set the format of the stream

        # Connect the new-sample signal from appsink to the callback
        self.appsink.connect('new-sample', self.on_new_sample, self.appsrc)

        # Add appsink and appsrc to the bin
        self.add(self.appsink)
        self.add(self.appsrc)

        # Create ghost pads for the bin
        self.add_pad(Gst.GhostPad.new('sink', self.appsink.get_static_pad('sink')))
        self.add_pad(Gst.GhostPad.new('src', self.appsrc.get_static_pad('src')))


    def on_new_sample(self, sink, appsrc):
        sample = sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.ERROR

        # Get the buffer and its associated caps (metadata)
        buffer = sample.get_buffer()
        caps = sample.get_caps()

        # Map buffer data to access image data
        result, map_info = buffer.map(Gst.MapFlags.READ)
        if not result:
            return Gst.FlowReturn.ERROR

        # Assuming the video frame data is in BGR format
        # Calculate the frame dimensions from the caps
        width = caps.get_structure(0).get_value('width')
        height = caps.get_structure(0).get_value('height')

        # Create a numpy array from the buffer data
        frame = np.ndarray(
            shape=(height, width, 3),
            dtype=np.uint8,
            buffer=map_info.data
        )

        # Modify the top left quadrant of the image to be black
        frame[:height//2, :width//2] = 0

        # Unmap the buffer after modifications
        buffer.unmap(map_info)

        # Create a new GstBuffer for output
        # This is necessary as the original buffer is readonly
        new_buffer = Gst.Buffer.new_wrapped(frame.tobytes())

        # Set the same caps on the new buffer
        new_buffer.set_caps(caps)

        # Push the modified buffer into appsrc
        appsrc.emit('push-buffer', new_buffer)

        return Gst.FlowReturn.OK


stop_requested = False


def check_stop_requested():
    print(f"check_stop_requesed: returning {stop_requested}")
    return stop_requested


class MyProcessingBin3a(Gst.Bin):


    def __init__(self):
        super().__init__()

        print("Creating a new MyProcessingBin3a")

        # Create appsink element
        self.appsink = Gst.ElementFactory.make('appsink', 'sink')
        self.appsink.set_property('emit-signals', True)  # Enable signal emitting to allow callbacks
        self.appsink.set_property('sync', False)  # Disable sync to process data as fast as possible

        # Connect the new-sample signal from appsink to the callback
        self.appsink.connect('new-sample', self.on_new_sample)

        # Add appsink and appsrc to the bin
        self.add(self.appsink)

        # Create ghost pads for the bin
        self.add_pad(Gst.GhostPad.new('sink', self.appsink.get_static_pad('sink')))


    def on_new_sample(self, sink):
        global stop_requested
        sample = sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.ERROR

        # Get the buffer and its associated caps (metadata)
        buffer = sample.get_buffer()
        caps = sample.get_caps()

        # Map buffer data to access image data
        result, map_info = buffer.map(Gst.MapFlags.READ)
        if not result:
            return Gst.FlowReturn.ERROR

        # Assuming the video frame data is in BGR format
        # Calculate the frame dimensions from the caps
        width = caps.get_structure(0).get_value('width')
        height = caps.get_structure(0).get_value('height')

        # Create a numpy array from the buffer data
        frame = np.ndarray(
            shape=(height, width, 3),
            dtype=np.uint8,
            buffer=map_info.data
        )

        result = np.array(frame)

        # Modify the top left quadrant of the image to be black
        result[:height//2, :width//2] = 0

        # Unmap the buffer after modifications
        buffer.unmap(map_info)

        # print("did the thing")
        stop_requested = True
        return Gst.FlowReturn.OK




mpb2 = MyProcessingBin2()
for pad in mpb2.iterate_pads():
    print("pad:", pad, pad.get_name(), pad.get_direction())

# def plugin_init(plugin):
#     print("plugin: ", plugin)
#     type_to_register = GObject.type_register(MyProcessingBin2)
#     Gst.Element.register(plugin, "myprocessingbin", 0, type_to_register)
#     return True


# Gst.Plugin.register_static(
#     Gst.VERSION_MAJOR,
#     Gst.VERSION_MINOR,
#     # "myprocessingplugin",
#     "myprocessingbin",
#     "Custom GStreamer Processing Plugin",
#     plugin_init,
#     "1.0",
#     "LGPL",
#     "MyProcessingPlugin",
#     "mycompany",
#     "https://mycompany.com"
# )


def pipeline_from_descriptor(pipeline_description):
    pipeline = Gst.parse_launch(pipeline_description)
    return pipeline


def enumerate_pads(element):
    print("element:", element, element.get_name())
    for pad in element.iterate_pads():
        print("  pad:", pad, pad.get_name(), pad.get_direction())


def manual_pipeline_construction(output=True):
    videotestsrc = Gst.ElementFactory.make("videotestsrc", "videotestsrc")
    enumerate_pads(videotestsrc)
    videoconvert0 = Gst.ElementFactory.make("videoconvert", "videoconvert0")
    enumerate_pads(videoconvert0)
    myprocessingbin = Gst.ElementFactory.make("myprocessingbin", "myprocessingbin")
    enumerate_pads(myprocessingbin)
    if output:
        videoconvert1 = Gst.ElementFactory.make("videoconvert", "videoconvert1")
        enumerate_pads(videoconvert1)
        fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
        enumerate_pads(fakesink)
    pipeline = Gst.Pipeline.new("mypipeline")
    pipeline.add(videotestsrc)
    pipeline.add(videoconvert0)
    videotestsrc.link(videoconvert0)
    pipeline.add(myprocessingbin)
    videoconvert0.link(myprocessingbin)
    if output:
        pipeline.add(videoconvert1)
        myprocessingbin.link(videoconvert1)
        pipeline.add(fakesink)
        videoconvert1.link(fakesink)
    return pipeline


if __name__ == "__main__":

    register(MyProcessingBin3a, "myprocessingbin")

    # Create pipeline
    pipeline_description = "videotestsrc ! videoconvert ! myprocessingbin ! videoconvert ! fakesink"
    # pipeline = pipeline_from_descriptor(pipeline_description)
    pipeline = manual_pipeline_construction(False)
    print("pipeline constructed")



    # Start pipeline
    pipeline.set_state(Gst.State.PLAYING)
    loop = GLib.MainLoop()
    # GLib.timeout_add_seconds(0.1, check_stop_requested)
    print("Starting pipeline...")
    Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, 'pipeline_state')
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        if loop and loop.is_running():
            loop.quit()
        pipeline.set_state(Gst.State.NULL)
        print("Pipeline stopped.")
