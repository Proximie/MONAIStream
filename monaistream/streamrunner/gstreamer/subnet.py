import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from monaistream.streamrunners.gstreamer.utils import parse_node_entry


class GstStreamRunnerSubnet:

    def __init__(self, runner, input_urls, output_urls):
        self.input_urls = input_urls
        self.output_urls = output_urls

        self.inputs = list()
        self.outputs = list()

        # validate that each name appears just once within its collection
        print(input_urls)
        input_name_set = set((u.name for u in input_urls))
        if len(input_name_set) != len(input_urls):
            raise ValueError("input names must be unique: got {input_name_set}")
        output_name_set = set((u.name for u in output_urls))
        if len(output_name_set) != len(output_urls):
            raise ValueError("output names must be unique: got {output_name_set}")

        # validate that the names are compatible with the runner
        print("input_urls:", input_urls)
        print("output_urls:", output_urls)
        print("input_names:", runner.input_names)
        print("output_names:", runner.output_names)
        for input_url in input_urls:
            if input_url.name not in runner.input_names:
                raise ValueError(f"input {input_url.name} not in {runner.input_names}")
        for output_url in output_urls:
            if output_url.name not in runner.output_names:
                raise ValueError(f"output {output_url.name} not in {runner.output_names}")

        self._pipeline = Gst.Pipeline().new("pipeline")
        for input_url in input_urls:
            element = parse_node_entry(input_url)
            self.inputs.append(element)
            print("element:", element)
            self._pipeline.add(element)

        self._pipeline.add(runner.backend)

        for output_url in output_urls:
            element = parse_node_entry(output_url)
            self.outputs.append(element)
            self._pipeline.add(element)

        for element, desc in zip(self.inputs, input_urls):
            print("input_desc pad name:", desc.name)
            element.link_pads("src", runner.backend, desc.name)

        for element, desc in zip(self.outputs, output_urls):
            print("output_desc pad name =", desc.name)
            print("element:", element)
            runner.backend.link_pads(desc.name, element, "sink")

    @property
    def pipeline(self):
        return self._pipeline
