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

from queue import Queue
from monai.transforms import Transform
from monai.utils.enums import CommonKeys


class StreamSinkTransform(Transform):
    def __init__(self, result_key: str = CommonKeys.PRED, buffer_size: int = 0, timeout: float = 1.0):
        super().__init__()
        self.result_key = result_key
        self.buffer_size = buffer_size
        self.timeout = timeout
        self.queue: Queue = Queue(self.buffer_size)

    def __call__(self, data):
        self.queue.put(data[self.result_key], timeout=self.timeout)
        return data

    def get_result(self):
        return self.queue.get(timeout=self.timeout)
