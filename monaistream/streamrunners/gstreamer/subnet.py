import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from monaistream.streamrunners.gstreamer.utils import parse_node_entry


class GstStreamRunnerSubnet:

    def __init__(self, input_urls, output_urls, runner):
        self.input_urls = input_urls
        self.output_urls = output_urls

        self.inputs = {}
        self.outputs = {}

        # validate that each name appears just once within its collection
        input_name_set = set((u.name for u in input_urls))
        if len(input_name_set) != len(input_urls):
            raise ValueError("input names must be unique: got {input_name_set}")
        output_name_set = set((u.name for u in output_urls))
        if len(output_name_set) != len(output_urls):
            raise ValueError("output names must be unique: got {output_name_set}")

        # validate that the names are compatible with the runner
        for input_url in input_urls:
            if input_url.name not in runner.input_names:
                raise ValueError(f"input {input_url.name} not in {runner.inputs_names}")
        for output_url in output_urls:
            if output_url.name not in runner.output_names:
                raise ValueError(f"output {output_url.name} not in {runner.output_names}")

        self._pipeline = Gst.Pipeline().new("pipeline")
        for input_url in input_urls:
            element = parse_node_entry(input_url.description)
            self.inputs.append(element)
            self._pipeline.add(element, input_url.name)

        for output_url in output_urls:
            element = parse_node_entry(output_url.description)
            self.outputs.append(element)
            self._pipeline.add(element, output_url.name)

        for element in self.inputs:
            element.link_pads("src", runner, element.get_name())

        for element in self.outputs:
            runner.link_pads(element.get_name(), element)
