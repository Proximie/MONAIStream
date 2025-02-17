from ignite.engine import Engine, Events
# from monai.engines.workflow import Workflow


class StreamingDataLoader:
    def __init__(self):
        self._payload = None

    def set_payload(self, payload):
        self._payload = payload

    def __iter__(self):
        return self

    def __next__(self):
        if self._payload is not None:
            return self._payload
        else:
            raise StopIteration()


class IgniteEngineAdaptor:

    def __init__(self, engine, data_loader=StreamingDataLoader()):
        self.running = False
        self.engine = engine
        self.engine.add_event_handler(Events.ITERATION_COMPLETED, self._interrupt)
        self.data_loader = data_loader

    def _interrupt(self):
        self.engine.interrupt()

    def _stop(self):
        self.running = False

    def __call__(self, src):
        # provide data sample 'src' to workflow dataset
        print("IgniteEngineAdaptor: __call__")
        self.data_loader.set_payload(src)
        self.engine.run(self.data_loader)
        print("engine.state.output:", type(self.engine.state.output))
        return self.engine.state.output
