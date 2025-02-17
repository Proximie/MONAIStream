import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

from monaistream.streamrunners.utils import run_pipeline
from monaistream.streamrunners.gstreamer_noplugin import create_dynamic_pipeline_class


# class BaseFoo:
#     def thing(self, *args, **kwargs):
#         raise NotImplementedError()


# def create_dynamic_subclass(name, thing):

#     SubClass = type(
#         name,
#         (BaseFoo,),
#         {
#             "thing": thing
#         }
#     )

#     return SubClass

# def sub_thing(self, action):
#     print(f"I am sub thing doing {action}")

# rclass = create_dynamic_subclass("SubFoo", sub_thing)

# x = BaseFoo()
# a = rclass()


# a.thing("bar")
# print(type(BaseFoo))
# print(type(x))
# print(type(rclass))
# print(type(a))


Gst.init(None)

def on_new_sample(sink, data=None):
    """Callback function for appsink sample event."""
    sample = sink.emit("pull-sample")
    print("on_new_sample")
    if sample:
        print("New sample received (push mode)")
    return Gst.FlowReturn.OK

def on_push_data(appsrc):
    """Callback function for pushing data to appsrc."""
    buffer = Gst.Buffer.new_allocate(None, 1024, None)
    buffer.fill(0, b"\x00" * 1024)
    appsrc.emit("push-buffer", buffer)


if __name__ == '__main__':

    pipeline_descriptor = (
        'videotestsrc is-live=true '
        '! videoconvert '
        '! queue '
        '! myapp '
        '! queue '
        '! videoconvert '
        '! fakesink'
    )

    DynamicPipelineBin = create_dynamic_pipeline_class(
        "appsrc name=myappsrc ! videoconvert ! appsink name=myappsink",
        on_new_sample_callback=on_new_sample,
        on_data_callback=on_push_data
    )

    run_pipeline(DynamicPipelineBin, 'myapp', pipeline_descriptor)


# # Register the Plugin
# def plugin_init(plugin):
#     type_to_register = GObject.type_register(DynamicPipelineBin)
#     return Gst.Element.register(plugin, DynamicPipelineBin.GST_PLUGIN_NAME, Gst.Rank.NONE, type_to_register)

# Gst.Plugin.register_static(
#     Gst.VERSION_MAJOR,
#     Gst.VERSION_MINOR,
#     "dynamicpipeline",
#     "Dynamically generated pipeline as a plugin",
#     plugin_init,
#     "1.0",
#     "LGPL",
#     "dynamicpipeline",
#     "example.com",
#     "https://example.com"
# )