# -*- coding: utf-8 -*-
"""Protobuf 解析器：读 ``FileDescriptorSet``（``protoc --descriptor_set_out`` 的产物）。

M0 骨架：**不做**文本解析（题面 §六 已弃选），只保留描述符入口与缺能力分类。
M2 实现 ``FieldDescriptorProto`` → :class:`~contractcompat.ir.Field` 的映射。

跨 message 字段号复用（R5 的增量格）需要文件级视图，故 M2 会把每个 message 的
``(message_name, field_number)`` 收进 IR 的 ``meta["messages"]``，由 M4 的 R5 求值。
"""

from __future__ import absolute_import

from ..errors import CapabilityError

__all__ = ["parse_descriptor_set", "protobuf_available"]


def protobuf_available():
    """探测 ``google.protobuf`` 是否可用（**不做猜测**：只回答"能不能 import"）。"""
    try:
        import google.protobuf  # noqa: F401
    except ImportError:
        return False
    return True


def parse_descriptor_set(path, require_complete_ir=False):
    if not protobuf_available():
        raise CapabilityError(
            "解析 FileDescriptorSet 需要 protobuf：请 `py -m pip install protobuf` 后重试（退出码 3 的既定语义）"
        )
    raise CapabilityError("FileDescriptorSet 解析计划在 M2 落地；当前为 M0 骨架，尚未实现")
