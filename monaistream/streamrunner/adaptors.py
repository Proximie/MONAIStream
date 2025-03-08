from typing import Any, Callable, Sequence
from ignite.engine import Events
from monai.engines.workflow import Workflow
from monai.engines.utils import default_prepare_batch,PrepareBatch
from torch import nn
import torch

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
    

class WorkflowEngineAdaptor:

    def __init__(self, engine:Workflow,data_loader):
        self.engine = engine
        self.data_loader = data_loader
        self.engine.add_event_handler(Events.ITERATION_COMPLETED, self._interrupt)

    def _interrupt(self):
        self.engine.interrupt()

    def __call__(self, src):
        print("IgniteEngineAdaptor: __call__")
        self.data_loader.set_payload(src)
        self.engine.run()
        print("engine.state.output:", type(self.engine.state.output))
        return self.engine.state.output


# class MultiInputNetworkAdaptor(nn.Module):
#     def __init__(self, network):
#         super().__init__()
#         self.network=network

#     def forward(self,inputs):
#         return [self.network(i) for i in inputs]


class ListPrepareBatch(PrepareBatch):
    def __init__(self,prepare_func:Callable=default_prepare_batch):
        self.prepare_func=prepare_func

    def __call__(
        self,
        batchdata: dict[str, torch.Tensor] | torch.Tensor | Sequence[torch.Tensor],
        device: str | torch.device | None = None,
        non_blocking: bool = False,
        **kwargs: Any,
    ) -> tuple[torch.Tensor, torch.Tensor | None] | torch.Tensor:
        batches=[self.prepare_func(i,device,non_blocking,**kwargs) for i in batchdata]
        inputs,labels=zip(*batches)

        if len(batches)==1:
            return inputs[0], labels[0]
        else:
            return inputs, labels
