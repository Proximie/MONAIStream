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

from typing import Callable

import torch

from queue import Empty, Queue
from threading import RLock


__all__ = ["IterableBufferDataset", "StreamSinkTransform"]


class IterableBufferDataset(torch.utils.data.IterableDataset):
    """Defines a iterable dataset using a Queue object to permit asynchronous additions of new items, eg. frames."""

    STOP = "STOP"  # stop sentinel used to indicate to the read thread to quit

    def __init__(self, transform: Callable, buffer_size: int = 0, timeout: float = 0.01):
        super().__init__()
        self.transform = transform
        self.buffer_size = buffer_size
        self.timeout = timeout
        self.buffer: Queue = Queue(self.buffer_size)
        self._is_running = False
        self._lock = RLock()

    @property
    def is_running(self):
        with self._lock:
            return self._is_running

    def add_item(self, item):
        """
        The idea is that the source of the streaming data would add items here and these would be consumed by the
        engine immediately. The engine's `run` method would be running in the main or some other thread separate from
        the source, eg. something reading from port or from a device which puts individual video frames here.
        """
        self.buffer.put(item, timeout=self.timeout)

    def stop(self):
        with self._lock:
            self._is_running = False

    def __iter__(self):
        """
        This will continually attempt to get an item from the queue until STOP is received or stop() called.
        """
        with self._lock:
            self._is_running = True

        try:
            while self.is_running:  # checking exit condition prevents deadlock
                try:
                    item = self.buffer.get(timeout=self.timeout)

                    if item == IterableBufferDataset.STOP:  # stop looping when sentinel received
                        break

                    yield self.transform(item)
                except Empty:
                    pass  # queue was empty this time, try again
        finally:
            self.stop()
