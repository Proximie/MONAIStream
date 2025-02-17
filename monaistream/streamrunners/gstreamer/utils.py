import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject


def register(runner_type, runner_alias):
    RunnerType = GObject.type_register(runner_type)
    if not Gst.Element.register(None, runner_alias, Gst.Rank.NONE, RunnerType):
        raise RuntimeError(f"Failed to register {runner_alias}; you may be missing gst-python plugins")



def create_registerable_plugin(base_type, class_name, do_op):
    # TODO: is this class actually gstreamer specific?
    def init_with_do_op(self):
        base_type.__init__(self, do_op)

    sub_class_type = type(
        class_name,
        (base_type,),
        {
            "__init__": init_with_do_op,
        }
    )

    return sub_class_type



def run_pipeline(pipeline):
    pipeline.set_state(Gst.State.PLAYING)

    loop = GLib.MainLoop()
    try:
        print("running loop")
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        print("shutting down")
        if pipeline:
            pipeline.send_event(Gst.Event.new_eos())
            bus = pipeline.get_bus()
            msg = bus.timed_pop_filtered(2 * Gst.SECOND, Gst.MessageType.EOS)
            pipeline.set_state(Gst.State.NULL)
            # pipeline.get_state(Gst.CLOCK_TIME_NONE)
        if loop and loop.is_running():
            loop.quit()
