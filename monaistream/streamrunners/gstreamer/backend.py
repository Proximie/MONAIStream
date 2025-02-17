import threading

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


import numpy as np


class GstStreamRunnerBackend(Gst.Element):
    __gstmetadata__ = ("GstStreamRunnerBackend", "Filter", "Overlay images", "Author")


    __gsttemplates__ = (
        Gst.PadTemplate.new("sink_0",
                            Gst.PadDirection.SINK,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, format=BGR, width=256, height=256")),
        Gst.PadTemplate.new("sink_1",
                            Gst.PadDirection.SINK,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, format=BGR, width=128, height=128")),
        Gst.PadTemplate.new("src_0",
                            Gst.PadDirection.SRC,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, width=256, height=256")),
        Gst.PadTemplate.new("src_1",
                            Gst.PadDirection.SRC,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, width=128, height=128")),
    )


    def __init__(self, do_op=None):
        super().__init__()
        self._lock = threading.Lock()

        self._do_op = do_op

        # Create pads
        self.sinkpad_0 = Gst.Pad.new_from_template(self.__gsttemplates__[0], "sink_0")
        self.sinkpad_1 = Gst.Pad.new_from_template(self.__gsttemplates__[1], "sink_1")
        self.srcpad_0 = Gst.Pad.new_from_template(self.__gsttemplates__[2], "src_0")
        self.srcpad_1 = Gst.Pad.new_from_template(self.__gsttemplates__[3], "src_1")

        # Set chain function for sink pads
        self.sinkpad_0.set_chain_function(self.do_chain)
        self.sinkpad_1.set_chain_function(self.do_chain)

        # Add pads
        self.add_pad(self.sinkpad_0)
        self.add_pad(self.sinkpad_1)
        self.add_pad(self.srcpad_0)
        self.add_pad(self.srcpad_1)

        self.buffer_0 = None
        self.buffer_1 = None


    def do_chain(self, pad, parent, buffer):

        with self._lock:
            print("=======================================")
            print(f"do_chain called on {pad.get_name()} with thread id {threading.get_ident()}")
            if pad == self.sinkpad_0:
                self.buffer_0 = buffer
            elif pad == self.sinkpad_1:
                self.buffer_1 = buffer
            else:
                print("Unexpected pad!")

            if self.buffer_0 and self.buffer_1:
                buffers = (self.buffer_0, self.buffer_1)


                frames = list()
                # for sinkpad in (self.sinkpad_0, self.sinkpad_1):
                for sinkpad, buffer in ((self.sinkpad_0, self.buffer_0), (self.sinkpad_1, self.buffer_1)):
                    # Extract data from buffer
                    success, map_info = buffer.map(Gst.MapFlags.READ)
                    if not success:
                        print("Unexpected failure!")
                        return Gst.FlowReturn.ERROR

                    caps = sinkpad.get_current_caps().get_structure(0)
                    # print("caps:", caps)
                    height, width, channels = caps.get_value("height"), caps.get_value("width"), caps.get_value("channels")
                    # print("data:", len(map_info.data))
                    frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
                    frames.append(frame)
                    buffer.unmap(map_info)

                self._do_op(frames)

                dframe = np.array(frames[0])

                dbuffer0 = Gst.Buffer.new_wrapped(dframe.tobytes())
                dbuffer1 = Gst.Buffer.new_wrapped(dframe.tobytes())

                # Push buffers downstream
                self.srcpad_0.push(dbuffer0)
                self.srcpad_1.push(dbuffer1)

            return Gst.FlowReturn.OK


    def do_op(self, sink_data):
        """
        When using do_op programatically, the user should set do_op in order to define the
        operation that gets performed on the buffers.
        When used as a plugin for gstreamer, do_op should be subclassed to carry out the intended
        operation.
        """
        if self._do_op is None:
            raise ValueError("do_op not set")
        self._do_op(sink_data)
