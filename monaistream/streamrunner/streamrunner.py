from dataclasses import dataclass

from monaistream.streamrunners.gstreamer.backend import GstStreamRunnerBackend



def parse_queue_policy(policy):
    # TODO: support queuing policies
    return lambda q: q



def parse_backend(backend, array_type):
    supported_backends = ("gstreamer",)
    if isinstance(backend, str):
        if backend == "gstreamer":
            return GstStreamRunnerBackend(array_type=array_type)
        else:
            raise ValueError(f"unknown backend {backend}; must be one of {supported_backends}")
    return GstStreamRunnerBackend()



def check_input_format(format):
    return format



def parse_node_entry(entry):
    return entry



class StreamRunner:

    def __init__(self,
                 input_configs=None,
                 output_configs=None,
                 queue_policy=None,
                 backend="gstreamer",
                 array_type="numpy",
                 do_op=None
    ):
        # TODO: support passing in a queue policy / queue backend
        # TODO: support selecting / passing in a backend
        # TODO: passing in inputs / outputs on init
        self._queue = parse_queue_policy(queue_policy)
        self._backend = parse_backend(backend, array_type)
        print("backend:", self._backend)
        self._backend.set_do_op(do_op)

        if input_configs is not None:
            for c in input_configs:
                self.add_input(c.name, c.format)
        if output_configs is not None:
            for c in output_configs:
                self.add_output(c.name, c.format)

    def add_input(self, name, format):
        return self._add_input_or_output(name, format, True)


    def remove_input(self, name):
        return self._remove_input_or_output(name, True)


    def add_output(self, name, format):
        return self._add_input_or_output(name, format, False)


    def remove_output(self, name):
        return self._remove_input_or_output(name, False)


    @property
    def input_names(self):
        return tuple(i.get_name() for i in self._backend.sinkpads)


    @property
    def output_names(self):
        return tuple(o.get_name() for o in self._backend.srcpads)


    @property
    def backend(self):
        return self._backend


    def register(self, name, permanent=False):
        raise NotImplementedError()


    def start(self):
        raise NotImplementedError()


    def stop(self, wait_timeout=None):
        raise NotImplementedError()


    def _add_input_or_output(self, name, format, is_input):
        # TODO: this should only be possible to do in certain StreamRunner states
        # TODO: name clash policy
        check_input_format(format)
        if is_input:
            self._backend.add_input(name, format)
        else:
            self._backend.add_output(name, format)


    def _remove_input_or_output(self, name, collection):
        # TODO: this should only be possible to do in certain StreamRunner states
        del collection[name]

        raise NotImplementedError()


