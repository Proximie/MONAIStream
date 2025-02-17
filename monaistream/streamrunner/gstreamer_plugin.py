import inspect
import threading

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
from gi.repository import Gst, GstBase

import numpy as np



FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"



class GstInPlaceStreamRunner(GstBase.BaseTransform):
    """
    TODO:
     - specify source/sink one of several ways:
       - pipeline descriptor string
       - presets that look up descriptor strings (with argument specification)
     - move runner class inside a factory class
       - the runner is constructed

    TODO: Turn into usage guidelines

    Gst.init()

    class MyInPlaceOp(GstInPlaceStreamRunner):

        def do_op(self, data):
            data += 1

    def run_pipeline(src_descriptor, dest_descriptor):

        register(MyInPlaceOp, 'myop')

        pipeline_descriptor = (
            f'{src_descriptor} '
            '! rtph264depay '
            '! avdec_h264 '
            '! videoconvert '
            '! queue '
            '! myop '
            '! queue '
            '! videoconvert '
            '! x264enc tune=zerolatency '
            '! rtph264pay '
            f'! {dest_descriptor}'
        )

        pipeline = Gst.parse_launch(pipeline_descriptor)

        pipeline.set_state(Gst.State.PLAYING)

        loop = GLib.MainLoop()
        try:
            print("running loop")
            loop.run()
        except KeyboardInterrupt:
            raise
        finally:
            pipeline.set_state(Gst.State.NULL)

    if __name__ == '__main__':

        run_pipeline(
            'udpsrc address=0.0.0.0 port=5001 caps=application/x-rtp,media=video,payout=96,encoding-name=H264',
            'udpsink host=255.255.255.255 port=5002'
        )
    """

    GST_PLUGIN_NAME = "gstinplacestreamrunner"

    __gstmetadata__ = ("Gst In Place Stream Runner", "Transform", "Description", "Author")

    __gsttemplates__ = (
        Gst.PadTemplate.new(
           "src", Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
        Gst.PadTemplate.new(
           "sink", Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
    )

    __gstproperties__ = {}

    def do_op(self, data):
        raise NotImplementedError()

    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        print("do_transform_ip")

        cstruct = self.srcpad.get_current_caps().get_structure(0)
        height = cstruct.get_value("height")
        width = cstruct.get_value("width")
        format = cstruct.get_value("format")

        is_mapped, map_info = buffer.map(Gst.MapFlags.WRITE)

        if is_mapped:
            data = np.ndarray((height, width, len(format)), dtype=np.uint8, buffer=map_info.data)
            data = self.do_op(data)
            buffer.unmap(map_info)
        else:
            raise RuntimeError("Mapping failed")

        return Gst.FlowReturn.OK



class GstAdaptorStreamRunner(GstBase.BaseTransform):
    """
    TODO:
     - specify source/sink one of several ways:
       - pipeline descriptor string
       - presets that look up descriptor strings (with argument specification)
     - move runner class inside a factory class
       - the runner is constructed

    TODO: Turn into usage guidelines

    Gst.init()

    class MyAdaptorOp(GstAdaptorStreamRunner):

        def do_op(self, src_data, snk_data):
            snk_data[...] = src_data[:snk_data.shape[0], :snk_data.shape[1], :]

    def run_pipeline(src_descriptor, dest_descriptor):

        register(MyAdaptorOp, 'myop')

        pipeline_descriptor = (
            f'{src_descriptor} '
            '! rtph264depay '
            '! avdec_h264 '
            '! videoconvert '
            '! queue '
            '! myop '
            '! queue '
            '! videoconvert '
            '! x264enc tune=zerolatency '
            '! rtph264pay '
            f'! {dest_descriptor}'
        )

        pipeline = Gst.parse_launch(pipeline_descriptor)

        pipeline.set_state(Gst.State.PLAYING)

        loop = GLib.MainLoop()
        try:
            print("running loop")
            loop.run()
        except KeyboardInterrupt:
            raise
        finally:
            pipeline.set_state(Gst.State.NULL)

    if __name__ == '__main__':

        run_pipeline(
            'udpsrc address=0.0.0.0 port=5001 caps=application/x-rtp,media=video,payout=96,encoding-name=H264',
            'udpsink host=255.255.255.255 port=5002'
        )
    """

    GST_PLUGIN_NAME = "gstadaptorstreamrunner"

    __gstmetadata__ = ("Adaptor Stream Runner", "Transform", "Description", "Author")

    __gsttemplates__ = (
        Gst.PadTemplate.new(
           "sink", Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
        Gst.PadTemplate.new(
           "src", Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
    )


    def __init__(self, width=None, height=None):
        super().__init__()
        self.width = width
        self.height = height


    def do_op(self, data):
        raise NotImplementedError()


    def do_get_property(self, prop):
        if prop.name == "width":
            return self.width
        elif prop.name == "height":
            return self.height
        else:
            raise AttributeError(f"No such property {prop.name}")


    def do_set_property(self, prop, value):
        if prop.name == "width":
            self.width = value
        elif prop.name == "height":
            self.height = value
        else:
            raise AttributeError(f"No such property {prop.name}")


    def do_transform(self, in_buffer: Gst.Buffer, out_buffer: Gst.Buffer) -> Gst.FlowReturn:

        in_cstruct = self.sinkpad.get_current_caps().get_structure(0)
        in_height = in_cstruct.get_value("height")
        in_width = in_cstruct.get_value("width")
        in_format = in_cstruct.get_value("format")

        out_cstruct = self.srcpad.get_current_caps().get_structure(0)
        out_height = out_cstruct.get_value("height")
        out_width = out_cstruct.get_value("width")
        out_format = out_cstruct.get_value("format")

        print(f"from ({in_height, in_width, in_format}) to ({out_height, out_width, out_format})")

        snk_is_mapped, snk_map_info = in_buffer.map(Gst.MapFlags.READ)
        src_is_mapped, src_map_info = out_buffer.map(Gst.MapFlags.WRITE)

        if snk_is_mapped and src_is_mapped:
            in_data = np.ndarray((in_height, in_width, len(in_format)), dtype=np.uint8, buffer=snk_map_info.data)
            out_data = np.ndarray((out_height, out_width, len(out_format)), dtype=np.uint8, buffer=src_map_info.data)
            self.do_op(in_data, out_data)
            in_buffer.unmap(snk_map_info)
            out_buffer.unmap(src_map_info)
        else:
            raise RuntimeError("Mapping failed: source mapping status={src_is_mapped}; sink mapping status={sink_is_mapped}")

        return Gst.FlowReturn.OK



class GstMultiInputStreamRunner(GstBase.Aggregator):

    __gstmetadata__ = ('MultiInputStreamRunner', 'Filter', 'StreamRunner for handling multiple inputs', 'MONAI')

    __gsttemplates__ = (
        Gst.PadTemplate.new(
           "sink_%u", Gst.PadDirection.SINK, Gst.PadPresence.REQUEST, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
        Gst.PadTemplate.new(
           "src", Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
    )


    def __init__(self):
        super().__init__()

        # TODO: support input and output buffer formats properties on the pipeline string

        self.input_count = 2


    def do_op(self, data):
        raise NotImplementedError()


    def collect_images(self, agg, pad, images):

        width = pad.get_current_caps().get_structure(0).get_int("width")[1]
        height = pad.get_current_caps().get_structure(0).get_int("height")[1]

        buf = pad.pop_buffer()
        success, map_info = buf.map(Gst.MapFlags.READ)

        img = np.frombuffer(map_info.data, dtype=np.uint8).reshape((width, height, 3))
        images.append(img)

        buf.unmap(map_info)

        return True


    def do_aggregate(self, timeout):
        images = list()
        self.foreach_sink_pad(self.collect_images, images)

        # Perform the overlay operation (placing overlay image at top-left corner)
        # main_image[:128, :128] = overlay_image  # Replace top-left region with overlay
        result = self.do_op(images)

        # Create a new buffer for output
        output_buffer = Gst.Buffer.new_wrapped(result.tobytes())

        # Push the output buffer
        self.srcpad.push(output_buffer)
        return Gst.FlowReturn.OK



class GstMultiInputStreamRunner2(GstBase.Aggregator):

    __gstmetadata__ = ('MultiInputStreamRunner2', 'Filter', 'StreamRunner for handling multiple inputs', 'MONAI')

    __gsttemplates__ = (
        Gst.PadTemplate.new(
           "sink_%u", Gst.PadDirection.SINK, Gst.PadPresence.REQUEST, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
        Gst.PadTemplate.new(
           "src", Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
    )


    def __init__(self):
        super(GstMultiInputStreamRunner2, self).__init__()
        self.input_pads = []  # Store requested pads


    def do_request_new_pad(self, templ, name, caps=None):
        """Handles dynamic pad creation when requested by the pipeline."""
        pad = self.request_pad(templ, name)
        if pad:
            print(f"Created sink pad: {pad.get_name()}")
            self.input_pads.append(pad)
        else:
            print(f"Failed to create sink pad: {name}")
        return pad


    def do_op(self, images):
        """Process images and return output image"""
        raise NotImplementedError()


    def do_aggregate(self):
        buffers = []
        map_infos = []
        images = []

        for pad in self.input_pads:
            aggregator_pad = GstBase.AggregatorPad.get_from_pad(pad)
            buffer = aggregator_pad.peek_buffer()
            if not buffer:
                return Gst.FlowReturn.ERROR

            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR

            buffers.append(buffer)
            map_infos.append(map_info)

            width = pad.get_current_caps().get_structure(0).get_int("width")[1]
            height = pad.get_current_caps().get_structure(0).get_int("height")[1]
            np_input = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
            images.append(np_input)

        # Perform operation on images
        result = self.do_op(images)

        for buffer, map_info in zip(buffers, map_infos):
            buffer.unmap(map_info)

        # Create a new buffer
        output_buffer = Gst.Buffer.new_allocate(None, result.nbytes, None)
        output_buffer.fill(0, result.tobytes())

        # Push the buffer to the src pad
        return self.finish_buffer(output_buffer)



class GstMultiInputStreamRunner3(GstBase.Aggregator):

    __gstmetadata__ = ('MultiInputStreamRunner3', 'Filter', 'StreamRunner for handling multiple inputs', 'MONAI')

    __gsttemplates__ = (
        Gst.PadTemplate.new(
           "sink_%u", Gst.PadDirection.SINK, Gst.PadPresence.REQUEST, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
        Gst.PadTemplate.new(
           "src", Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")
        ),
    )


    def __init__(self):
        super(GstMultiInputStreamRunner3, self).__init__()
        self.input_pads = []  # Store requested pads


    def do_start(self):
        """Ensure pads are created when the element starts."""
        print("Initializing GstMultiInputStreamRunner, creating sink pads...")
        for i in range(2):  # Ensure two sink pads exist
            pad = self.request_pad(self.get_pad_template("sink_%u"), f"sink_{i}")
            if pad:
                print(f"Created sink pad: {pad.get_name()}")
                pad.set_active(True)  # Ensure pad is active
                self.input_pads.append(pad)
            else:
                print(f"Failed to create sink pad {i}")
                return False


    def do_op(self, images):
        """Process images and return output image"""
        raise NotImplementedError()


    def do_aggregate(self):
        buffers = []
        map_infos = []
        images = []

        for pad in self.input_pads:
            aggregator_pad = GstBase.AggregatorPad.get_from_pad(pad)
            buffer = aggregator_pad.peek_buffer()
            if not buffer:
                return Gst.FlowReturn.ERROR

            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR

            buffers.append(buffer)
            map_infos.append(map_info)

            width = pad.get_current_caps().get_structure(0).get_int("width")[1]
            height = pad.get_current_caps().get_structure(0).get_int("height")[1]
            np_input = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
            images.append(np_input)

        # Perform operation on images
        result = self.do_op(images)

        for buffer, map_info in zip(buffers, map_infos):
            buffer.unmap(map_info)

        # Create a new buffer
        output_buffer = Gst.Buffer.new_allocate(None, result.nbytes, None)
        output_buffer.fill(0, result.tobytes())

        # Push the buffer to the src pad



class GstMultiInOutStreamRunnerPrototype1(Gst.Element):
    __gstmetadata__ = ('GstMultiInOutStreamRunnerPrototype1', 'Filter', 'StreamRunner for handling multiple inputs and outputs', 'MONAI')


    def __init__(self, input_formats, output_formats):
        super().__init__()

        # Create sink pads (inputs)
        self.input_pads = list()
        for i_f, f in enumerate(input_formats):
            pad = Gst.Pad.new_from_static_template(self.get_pad_template("sink_%u"), f"sink_{i_f}")
            self.add_pad(pad)
            self.input_pads.append(pad)

        # Create src pads (outputs)
        self.output_pads = list()
        for i_f, f in enumerate(output_formats):
            pad = Gst.Pad.new_from_static_template(self.get_pad_template("sink_%u"), f"sink_{i_f}")
            self.add_pad(pad)
            self.output_pads.append(pad)


    # TODO: what are parent and buffer for?
    def do_chain(self, pad, _parent, _buffer):
        """Handles incoming buffers on both sink pads and processes them."""

        # TODO: is this the right way to handle situations where one of the inputs is the
        # "main" input?
        # active_input_pad_index = None
        # try:
        #     active_input_pad_index = self.input_pads.index(pad)
        # except ValueError:
        #     raise Gst.FlowReturn.ERROR

        # map all the sources
        buffers = list()
        map_infos = list()
        images = list()
        for i_p, p in enumerate(self.input_pads):
            b = p.get_current_buffer()
            buffers.append(b)
            success, map_info = b.map(Gst.MapFlags.READ)
            # TODO: we should be more robust than this
            if not success:
                return Gst.FlowReturn.ERROR

            map_infos.append(map_info)

            np_input = np.frombuffer(map_info.data, dtype=np.uint8).reshape(self.input_pads[i_p].shape)
            images.append(np_input)

        # TODO: map outputs here
        # perform user-defined operation
        results = self.do_op(images)

        # push outputs
        if len(results) != len(self.output_pads):
            raise ValueError("there must be as many results as there are output pads")

        for i_r, r in enumerate(results):
            o_buffer = Gst.Buffer.new_wrapped(r.tobytes())
            self.output_pads[i_r].append(o_buffer)

        return Gst.FlowReturn.OK



class GstMultiInOutStreamRunnerPrototype2(Gst.Element):
    __gstmetadata__ = ("GstMultiInOutStreamRunnerPrototype2", "Filter", "Overlay images", "Author")

    __gsttemplates__ = (
        Gst.PadTemplate.new("sink_1",
                            Gst.PadDirection.SINK,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, width=256, height=256")),
        Gst.PadTemplate.new("sink_2",
                            Gst.PadDirection.SINK,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, width=128, height=128")),
        Gst.PadTemplate.new("src_1",
                            Gst.PadDirection.SRC,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, width=256, height=256")),
        Gst.PadTemplate.new("src_2",
                            Gst.PadDirection.SRC,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, width=128, height=128")),
    )

    def __init__(self):
        super().__init__()

        # Pads
        self.sinkpad_1 = Gst.Pad.new_from_template(
            self.__gsttemplates__[0], "sink_1")
        self.sinkpad_2 = Gst.Pad.new_from_template(
            self.__gsttemplates__[1], "sink_2")
        self.srcpad_1 = Gst.Pad.new_from_template(
            self.__gsttemplates__[2], "src_1")
        self.srcpad_2 = Gst.Pad.new_from_template(
            self.__gsttemplates__[3], "src_2")

        self.add_pad(self.sinkpad_1)
        self.add_pad(self.sinkpad_2)
        self.add_pad(self.srcpad_1)
        self.add_pad(self.srcpad_2)

        self.buffer_1 = None
        self.buffer_2 = None

    def do_chain(self, pad, parent, buffer):

        print("do_chain")
        if pad == self.sinkpad_1:
            self.buffer_1 = buffer
        elif pad == self.sinkpad_2:
            self.buffer_2 = buffer

        if self.buffer_1 and self.buffer_2:
            # Process overlay using GStreamer compositor or blending
            # (this is a simplified approach; normally, you'd use a Gst.VideoMixer or Gst.OverlayComposition)

            # Push buffer_1 with buffer_2 overlaid on top-left
            self.srcpad_1.push(self.buffer_1)
            # Push buffer_2 with buffer_1 overlaid on top-left
            self.srcpad_2.push(self.buffer_2)

        return Gst.FlowReturn.OK


class GstMultiInOutStreamRunnerPrototype3(Gst.Element):
    __gstmetadata__ = ("GstMultiInOutStreamRunnerPrototype3", "Filter", "Overlay images", "Author")
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
                            Gst.Caps.from_string("video/x-raw, format=BGR, width=256, height=256")),
        Gst.PadTemplate.new("src_1",
                            Gst.PadDirection.SRC,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.from_string("video/x-raw, format=BGR, width=128, height=128")),
    )


    def __init__(self, do_op=None):
        super().__init__()
        self._lock = threading.Lock()

        self._do_op = do_op

        # Create pads from templates
        self.sinkpad_0 = Gst.Pad.new_from_template(
            self.__gsttemplates__[0], "sink_0")
        self.sinkpad_1 = Gst.Pad.new_from_template(
            self.__gsttemplates__[1], "sink_1")
        self.srcpad_0 = Gst.Pad.new_from_template(
            self.__gsttemplates__[2], "src_0")
        self.srcpad_1 = Gst.Pad.new_from_template(
            self.__gsttemplates__[3], "src_1")

        # Set chain functions for sink pads
        self.sinkpad_0.set_chain_function(self.chain_0)
        self.sinkpad_1.set_chain_function(self.chain_1)

        # Add pads to element
        self.add_pad(self.sinkpad_0)
        self.add_pad(self.sinkpad_1)
        self.add_pad(self.srcpad_0)
        self.add_pad(self.srcpad_1)

        self.buffer_0 = None
        self.buffer_1 = None


    def chain_0(self, pad, parent, buffer):
        with self._lock:
            print(f"chain_0 called on thread {threading.get_ident()}")
            self.buffer_0 = buffer
            if self.buffer_1:
                self.process_buffers()
            return Gst.FlowReturn.OK


    def chain_1(self, pad, parent, buffer):
        with self._lock:
            print(f"chain_1 called on thread {threading.get_ident()}")
            self.buffer_1 = buffer
            if self.buffer_0:
                self.process_buffers()
            return Gst.FlowReturn.OK


    def process_buffers(self):
        print("=================================")
        print(f"process_buffers called on thread {threading.get_ident()}")
        # Process and push to both source pads

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
        print("doing op")
        if self._do_op is None:
            raise ValueError("do_op not set")
        self._do_op(sink_data)
