# -*- coding: utf-8 -*-
"""错误类型：把"调用方写错"与"这台机器给不了"分成两类异常。

退出码映射唯一在 ``cli.main``；本模块只定义类型，不做 IO、不打印。
``data/README.md`` §4.5 是退出码的唯一定义处：
  2 = 用法 / 输入错误（调用方写错）
  3 = 环境或能力不满足（环境给不了）
"""


class ContractCompatError(Exception):
    """本包所有可预期错误的基类。"""

    exit_code = 2


class UsageError(ContractCompatError):
    """调用方写错：文件不存在、参数矛盾、transitive 缺 history、未知 policy。"""

    exit_code = 2


class SchemaParseError(UsageError):
    """输入不是合法的 schema：非法 JSON / 非法描述符 / 结构不符。"""


class CapabilityError(ContractCompatError):
    """环境给不了：缺 protoc、缺 protobuf 包、IR 不可表达而要求完整。"""

    exit_code = 3


class NotYetImplemented(CapabilityError):
    """本版还没有该能力（骨架期的显式出口）。

    刻意归到退出码 3 而不是 0：**未实现绝不能看起来像"没问题"**（返回 0 的空壳
    会让调用方把"没检查"读成"检查通过"）。消息里必须写清计划在哪个里程碑落地。
    """

    exit_code = 3


class CanonicalError(UsageError):
    """规范 JSON 读写失败（非法 JSON / 顶层不是对象）。"""
