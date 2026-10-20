# -*- coding: utf-8 -*-
"""测试夹具：让 `src/` 布局在未安装时也能跑（安装后走正常 import）。

**不隐藏缺件**：`contractcompat` 装不上仍会在这里炸出来，不会静默 skip。
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import contractcompat  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.join(ROOT, "src"))
