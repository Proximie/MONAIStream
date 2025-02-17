import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


def create_dynamic_pipeline_class2(pipeline_desc, on_new_sample_callback=None, on_data_callback=None):
    """
    Dynamically creates a Gst.Bin subclass that wraps a given pipeline descriptor.
    """

    class_name = "DynamicPipelineBin"
#
    def __init__(self):
        super(self.__class__, self).__init__()

        pipeline = Gst.parse_launch(pipeline_desc)

        self.appsrc = pipeline.get_by_name("myappsrc")
        self.appsink = pipeline.get_by_name("myappsink")

        if self.appsink:
            self.appsink.set_property("emit-signals", True)
            self.appsink.set_property("sync", False)

            if on_new_sample_callback:
                self.appsink.connect("new-sample", on_new_sample_callback)

        if self.appsrc:
            if on_data_callback:
                self.push_data = on_data_callback

        for element in pipeline.children:
            self.add(element)

        # self.appsrc.link(self.appsink)

        self.add_pad(Gst.GhostPad.new("sink", self.appsrc.get_static_pad("sink")))
        self.add_pad(Gst.GhostPad.new("src", self.appsink.get_static_pad("src")))


    DynamicBin = type(
        class_name,
        (Gst.Bin,),
        {
            "__init__": __init__,
            "GST_PLUGIN_NAME": class_name.lower(),
        }
    )

    return DynamicBin


def create_dynamic_pipeline_class(pipeline_desc, on_new_sample_callback=None, on_data_callback=None):
    """
    Dynamically creates a Gst.Bin subclass that wraps a given pipeline descriptor.
    """

    class_name = "DynamicPipelineBin"

    def __init__(self):
        super(self.__class__, self).__init__()

        # Create an internal pipeline using Gst.parse_launch
        pipeline = Gst.parse_launch(pipeline_desc)

        # Extract appsrc and appsink
        self.appsrc = pipeline.get_by_name("myappsrc")
        self.appsink = pipeline.get_by_name("myappsink")

        if self.appsink:
            self.appsink.set_property("emit-signals", True)
            self.appsink.set_property("sync", False)

            if on_new_sample_callback:
                self.appsink.connect("new-sample", on_new_sample_callback)

        if self.appsrc and on_data_callback:
            self.push_data = on_data_callback

        # Add all pipeline elements to the bin
        for element in pipeline.children:
            pipeline.remove(element)  # Remove from original pipeline before adding to bin
            self.add(element)

        # Ensure ghost pads match the bin's expected external connections
        if self.appsrc:
            src_pad = self.appsrc.get_static_pad("src")
            if src_pad and not self.get_static_pad("sink"):
                self.add_pad(Gst.GhostPad.new("sink", src_pad))

        if self.appsink:
            sink_pad = self.appsink.get_static_pad("sink")
            if sink_pad and not self.get_static_pad("src"):
                self.add_pad(Gst.GhostPad.new("src", sink_pad))

    DynamicBin = type(
        class_name,
        (Gst.Bin,),
        {
            "__init__": __init__,
            "GST_PLUGIN_NAME": class_name.lower(),
        }
    )

    return DynamicBin


def create_registerable_plugin(base_type, class_name, do_op):

    def init_with_do_op(self):
        # super(class_name, self).__init__(do_op)
        base_type.__init__(self, do_op)

    sub_class_type = type(
        class_name,
        (base_type,),
        {
            "__init__": init_with_do_op,
        }
    )

    return sub_class_type
