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

import logging
from typing import TYPE_CHECKING, Any, Callable, Sequence

import torch
from monai.data import Dataset
from monai.engines import SupervisedEvaluator, default_metric_cmp_fn, default_prepare_batch
from monai.handlers import MeanSquaredError, from_engine
from monai.inferers import Inferer
from monai.transforms import Transform, apply_transform
from monai.utils import CommonKeys, ForwardMode, min_version, optional_import
from monai.utils.enums import IgniteInfo
from torch.nn import Module

if TYPE_CHECKING:
    from ignite.engine import Engine, Events, EventEnum
    from ignite.metrics import Metric
else:
    version = IgniteInfo.OPT_IMPORT_VERSION
    Engine, _ = optional_import("ignite.engine", version, min_version, "Engine", as_type="decorator")
    Metric, _ = optional_import("ignite.metrics", version, min_version, "Metric", as_type="decorator")
    Events, _ = optional_import("ignite.engine", version, min_version, "Events", as_type="decorator")
    EventEnum, _ = optional_import("ignite.engine", version, min_version, "EventEnum", as_type="decorator")


class SimpleInferenceEngine:
    """
    A simple engine-like class is for running inference on a per-input basis, such as with per-frame data in a
    video stream. It relies on a supplied Inferer instance and a network.
    """

    def __init__(
        self, inferer: Inferer, network: Module, preprocess: Callable | None = None, postprocess: Callable | None = None
    ):
        self.inferer = inferer
        self.network = network
        self.preprocess = preprocess
        self.postprocess = postprocess

    def __call__(self, inputs: torch.Tensor, *args: Any, **kwargs: Any) -> Any:
        if self.preprocess:
            inputs = apply_transform(self.preprocess, inputs)

        outputs = self.inferer(inputs, self.network, *args, **kwargs)

        if self.postprocess:
            outputs = apply_transform(self.postprocess, outputs)

        return outputs


class SingleItemDataset(Dataset):
    """
    This simple dataset only ever has one item and acts as its own iterable. This is used with InferenceEngine to
    represent a changeable single item epoch.
    """

    def __init__(self, transform: Sequence[Callable] | Callable | None = None) -> None:
        super().__init__([None], transform)

    def set_item(self, item):
        self.data[0] = item

    def __iter__(self):
        item = self.data[0]

        # TODO: use standard way of adding batch dimensions
        if isinstance(item, torch.Tensor):
            yield item[None]
        else:
            yield {k: v[None] for k, v in item.items()}


class InferenceEngine(SupervisedEvaluator):
    """
    A simple inference engine type for applying inference to one input at a time as a callable. This is meant to be used
    for inference on per-frame video stream data where the state of the engine and other setup should be done initially
    but reused for every frame. This allows for synchronous use of an engine class rather than running one in a separate
    thread.
    """

    def __init__(
        self,
        device: torch.device,
        network: torch.nn.Module,
        preprocessing: Transform | None = None,
        non_blocking: bool = False,
        prepare_batch: Callable = default_prepare_batch,
        iteration_update: Callable[[Engine, Any], Any] | None = None,
        inferer: Inferer | None = None,
        postprocessing: Transform | None = None,
        key_val_metric: dict[str, Metric] | None = None,
        additional_metrics: dict[str, Metric] | None = None,
        metric_cmp_fn: Callable = default_metric_cmp_fn,
        handlers: Sequence | None = None,
        amp: bool = False,
        event_names: list[str | EventEnum | type[EventEnum]] | None = None,
        event_to_attr: dict | None = None,
        decollate: bool = True,
        to_kwargs: dict | None = None,
        amp_kwargs: dict | None = None,
        compile: bool = False,
        compile_kwargs: dict | None = None,
        use_interrupt: bool = True,
    ) -> None:
        super().__init__(
            device=device,
            val_data_loader=SingleItemDataset(preprocessing),
            epoch_length=1,
            network=network,  # TODO: auto-convert to given device?
            inferer=inferer,
            non_blocking=non_blocking,
            prepare_batch=prepare_batch,
            iteration_update=iteration_update,
            postprocessing=postprocessing,
            key_val_metric=key_val_metric,
            additional_metrics=additional_metrics,
            metric_cmp_fn=metric_cmp_fn,
            val_handlers=handlers,
            amp=amp,
            mode=ForwardMode.EVAL,
            event_names=event_names,
            event_to_attr=event_to_attr,
            decollate=decollate,
            to_kwargs=to_kwargs,
            amp_kwargs=amp_kwargs,
            compile=compile,
            compile_kwargs=compile_kwargs,
        )

        self.logger.setLevel(logging.ERROR)  # probably don't want output for every frame
        self.use_interrupt = use_interrupt

        if use_interrupt:
            self.add_event_handler(Events.ITERATION_COMPLETED, self.interrupt)

    def __call__(self, item: Any, include_metrics: bool = False) -> Any:
        self.data_loader.set_item(item)
        self.run()

        out = self.state.output[0][CommonKeys.PRED]

        if include_metrics:
            return out, dict(self.state.metrics)
        else:
            return out


if __name__ == "__main__":
    net = torch.nn.Identity()
    engine = InferenceEngine(
        network=net,
        device="cpu",
        key_val_metric={"mse": MeanSquaredError(output_transform=from_engine([CommonKeys.IMAGE, CommonKeys.PRED]))},
    )
    print(engine(torch.rand(1, 5, 5)))
    print(engine(torch.rand(1, 6, 6), True))
