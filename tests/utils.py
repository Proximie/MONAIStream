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

import unittest

import torch
from monai.utils.module import optional_import


class SkipIfNoModule:
    """Decorator to be used if test should be skipped when optional module is not present."""

    def __init__(self, module_name):
        self.module_name = module_name
        self.module_missing = not optional_import(self.module_name)[1]
        self.deco = unittest.skipIf(self.module_missing, f"Optional module not present: {self.module_name}")

    def __call__(self, obj):
        return self.deco(obj)


def skip_if_no_cuda(obj):
    """
    Skip the unit tests if torch.cuda.is_available is False.
    """
    return unittest.skipUnless(torch.cuda.is_available(), "Skipping CUDA-based tests")(obj)
