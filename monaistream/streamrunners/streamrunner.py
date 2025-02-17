from dataclasses import dataclass

from monaistream.streamrunners.gstreamer.backend import GstStreamRunnerBackend



def parse_queue_policy(policy):
    # TODO: support queuing policies
    return lambda q: q



def parse_backend(backend):
    return GstStreamRunnerBackend()



def check_input_format(format):
    return format



def parse_node_entry(entry):
    return entry



@dataclass(frozen=True)
class NodeEntry:
    name: str
    url: str



class StreamRunner:

    def __init__(self, queue_policy=None, backend=None):
        # TODO: support passing in a queue policy / queue backend
        # TODO: support selecting / passing in a backend
        # TODO: passing in inputs / outputs on init

        self._queue = parse_queue_policy(queue_policy)
        self._backend = parse_backend(backend)


    def add_input(self, name, format):
        return self._add_input_or_output(name, format, self.inputs)


    def remove_input(self, name):
        return self._remove_input_or_output(name, self.inputs)


    def add_output(self, name, format):
        return self._add_input_or_output(name, format, self.outputs)


    def remove_output(self, name):
        return self._remove_input_or_output(name, self.outputs)


    @property.getter
    def backend(self):
        return self._backend


    def register(self, name, permanent=False):
        raise NotImplementedError()


    def start(self):
        raise NotImplementedError()


    def stop(self, wait_timeout=None):
        raise NotImplementedError()


    def _add_input_or_output(self, name, format, collection):
        # TODO: this should only be possible to do in certain StreamRunner states
        # TODO: name clash policy
        check_input_format(format)
        collection[name] = format

        raise NotImplementedError()


    def _remove_input_or_output(self, name, collection):
        # TODO: this should only be possible to do in certain StreamRunner states
        del collection[name]

        raise NotImplementedError()


