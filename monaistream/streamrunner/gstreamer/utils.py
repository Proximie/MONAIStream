# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from dataclasses import dataclass

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject


from contextlib import contextmanager
import numpy as np

from gi.repository import Gst, GstVideo

__all__ = ["BYTE_FORMATS", "get_dtype_from_bits", "map_buffer_to_numpy"]


BYTE_FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR,GRAY8,GRAY16_BE,GRAY16_LE}"


def parse_node_entry(entry):
    element = Gst.parse_bin_from_description_full(
        # entry.description, False, None, Gst.ParseFlags.NO_SINGLE_ELEMENT_BINS)
        entry.description, True, None, Gst.ParseFlags.PLACE_IN_BIN)

    if not element:
        raise ValueError(f"Failed to parse element {entry.description}")

    return element



def register(runner_type, runner_alias):
    RunnerType = GObject.type_register(runner_type)
    if not Gst.Element.register(None, runner_alias, Gst.Rank.NONE, RunnerType):
        raise ValueError(f"Failed to register {runner_alias}; you may be missing gst-python plugins")



def create_registerable_plugin(base_type, class_name, inputs, outputs, do_op):
    # TODO: is this class actually gstreamer specific?
    def init_with_do_op(self):
        base_type.__init__(self, inputs=inputs, outputs=outputs, do_op=do_op)

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
    print("logging pipeline graph")
    Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, 'pipeline_state')

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



@dataclass(frozen=True)
class PadEntry:
    name: str
    format: str



@dataclass(frozen=True)
class SubnetEntry:
    name: str
    description: str



def get_video_pad_template(
    name, direction=Gst.PadDirection.SRC, presence=Gst.PadPresence.ALWAYS, caps_str=f"video/x-raw,format={BYTE_FORMATS}"
):
    """
    Create a pad from the given template components. 
    """
    return Gst.PadTemplate.new(name, direction, presence, Gst.Caps.from_string(caps_str))


def get_dtype_from_bits(bits):
    """
    Get the dtype from the given element size based on assumptions about pixel formats (so not accurate or complete).
    """
    if bits == 8:
        return np.uint8
    elif bits == 16:
        return np.uint16
    elif bits == 32:
        return np.uint32  # TODO: or float32?
    else:
        raise ValueError(f"No obvious dtype for data items of size {bits}.")


def get_components(cformat):
    """
    Get the number of components for each pixel format, including padded components such as in RGBx.
    """
    if cformat in ("RGB","BGR"):
        return 3
    if cformat in ("RGBx","BGRx","xRGB","xBGR","RGBA","BGRA","ARGB","ABGR"):
        return 4
    if cformat in ("GRAY8","GRAY16_BE","GRAY16_LE"):
        return 1

    raise ValueError(f"Format `{cformat}` does not have a known number of components.") 
    

@contextmanager
def map_buffer_to_numpy(buffer, flags, caps, dtype=None):
    """
    Map the given buffer with the given flags and the capabilities from its associated pad. The dtype is inferred if not
    given which may be inaccurate for certain formats. The context object is a Numpy array for the buffer which is
    unmapped when the context exits. 
    """
    cstruct = caps.get_structure(0)
    height = cstruct.get_value("height")
    width = cstruct.get_value("width")
    cformat = cstruct.get_value("format")

    fstruct = GstVideo.video_format_from_string(cformat)
    ifstruct = GstVideo.video_format_get_info(fstruct)

    if dtype is None:
        dtype = get_dtype_from_bits(ifstruct.bits)

    dtype=np.dtype(dtype)
    is_mapped, map_info = buffer.map(flags)
    if not is_mapped:
        raise ValueError(f"Buffer {buffer} failed to map with flags `{flags}`.")

    shape = (height, width, get_components(cformat))

    expected_size = np.product(shape) * dtype.itemsize
    if expected_size != buffer.get_size():
        raise ValueError(
            f"Buffer size {buffer.get_size()} does not match expected size "
            "{expected_size} for shape {shape} and format {cformat}."
        )

    # TODO: byte order for gray formats

    bufarray = np.ndarray(shape, dtype=dtype, buffer=map_info.data)
    
    try:
        yield bufarray
    finally:
        buffer.unmap(map_info)


