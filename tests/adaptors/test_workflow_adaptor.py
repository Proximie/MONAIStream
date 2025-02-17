import unittest

from ignite.engine.engine import Engine

import monai
from monai.engines import Workflow

from monaistream.streamrunner.adaptors import IgniteEngineAdaptor


class TestIgniteEngineAdaptor(unittest.TestCase):

    def test_engine_adaptor(self):

        # def dummy_dataset(max_iterations):
        #     def _inner(self):
        #         for i in range(0, max_iterations):
        #             yield i
        #     return _inner

        class DummyDataset:
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

        class DummyModel:
            def __init__(self):
                pass

            def __call__(self, engine, foo):
                return foo

        outputs = list()

        e = Engine(DummyModel())
        dl = DummyDataset()
        ie = IgniteEngineAdaptor(e, dl)
        for i in range(10):
            result = ie(i)
            outputs.append(result.output)

        self.assertSequenceEqual(outputs, [i for i in range(10)])

if __name__ == "__main__":
    unittest.main()
