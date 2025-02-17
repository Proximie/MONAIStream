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
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

import torch

from monai.data import Dataset, DataLoader
from monai.engines import SupervisedEvaluator, default_metric_cmp_fn, default_prepare_batch
from monai.inferers import Inferer
from monai.transforms import Transform
from monai.utils import CommonKeys, ForwardMode, min_version, optional_import
from monai.utils.enums import IgniteInfo

if TYPE_CHECKING:
    from ignite.engine import Engine, Events, EventEnum
    from ignite.metrics import Metric
else:
    version = IgniteInfo.OPT_IMPORT_VERSION
    Engine, _ = optional_import("ignite.engine", version, min_version, "Engine", as_type="decorator")
    Metric, _ = optional_import("ignite.metrics", version, min_version, "Metric", as_type="decorator")
    Events, _ = optional_import("ignite.engine", version, min_version, "Events", as_type="decorator")
    EventEnum, _ = optional_import("ignite.engine", version, min_version, "EventEnum", as_type="decorator")


__all__ = ["SingleItemDataset", "RingBufferDataset", "CallableEvaluator"]


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
        item = self[0]

        # TODO: use standard way of adding batch dimensions, or do something specific here
        # for how groups of frames would be passed?
        if isinstance(item, torch.Tensor):
            yield item[None]
        elif isinstance(item, Sequence):
            yield tuple(v[None] for v in item)
        else:
            yield {k: v[None] for k, v in item.items()}


class RingBufferDataset(SingleItemDataset):
    def __init__(self, num_values=1, transform: Sequence[Callable] | Callable | None = None) -> None:
        super().__init__(transform)
        self.num_values = num_values

    def set_item(self, item):
        if self.data[0] is None:
            self.data[0] = (item,) * self.num_values
        else:
            self.data[0] = self.data[0][1:] + (item,)


class CallableEvaluator(SupervisedEvaluator):
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
        data_loader: Iterable | DataLoader | None = None,
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
        use_interrupt: bool = False,
    ) -> None:
        super().__init__(
            device=device,
            val_data_loader=data_loader if data_loader is not None else SingleItemDataset(preprocessing),
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
