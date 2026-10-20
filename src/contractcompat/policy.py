# -*- coding: utf-8 -*-
"""方向性判定核：七档 policy + 差异项方向判定。

口径（七档语义、buf 四档映射）唯一定义在 ``data/README.md`` §4.1 / §4.2；
本模块只实现它，并在 ``MAPPING_NOTES`` 里保留"只表达最接近、不宣称等价"的声明。

M0 骨架：``POLICIES`` / ``TRANSITIVE`` / ``mapping_table`` 已实现且被测试锁住；
``diff`` / ``judge`` 的函数体留 M3。
"""

from __future__ import absolute_import

from .errors import UsageError

__all__ = [
    "POLICIES",
    "TRANSITIVE",
    "DIRECTIONS",
    "VERDICTS",
    "MAPPING_NOTES",
    "resolve_policy",
    "mapping_table",
    "diff",
    "judge",
]

POLICIES = (
    "backward",
    "backward-transitive",
    "forward",
    "forward-transitive",
    "full",
    "full-transitive",
    "none",
)

TRANSITIVE = tuple(name for name in POLICIES if name.endswith("-transitive"))

#: 差异项的方向是**事实**，policy 是**选择**：换 policy 不改变 direction。
DIRECTIONS = ("BACKWARD_OK", "FORWARD_OK", "BOTH_OK", "NONE_OK")

VERDICTS = ("compatible", "breaking")

#: buf 四档映射。必须逐行带"关系说明"，且整表必须含"只表达最接近、不宣称等价"
#: （`data/README.md` §4.2 的使用规则；`tests/test_policy.py` 逐行断言）。
MAPPING_NOTES = (
    "本表只表达最接近，不宣称等价：buf 的档位是'检查哪些规则'，"
    "本题的 policy 是'允许哪个方向'，两者维度不同，因而不等价。"
)

_MAPPING_ROWS = (
    {
        "policy": "backward",
        "buf_tier": "WIRE（JSON 视图取 WIRE_JSON）",
        "relation": "buf 的档 = 检查哪些规则；本题的 policy = 允许哪个方向。二者维度不同，不等价",
        "buf_note": "buf 只判 Protobuf 线上字节，不含 Avro / JSON Schema",
    },
    {
        "policy": "forward",
        "buf_tier": "无直接对应",
        "relation": "buf 不区分方向，只判'是否破坏'；本题显式区分方向",
        "buf_note": "因此本档没有可对齐的 buf 档位",
    },
    {
        "policy": "full",
        "buf_tier": "WIRE + WIRE_JSON 同时通过",
        "relation": "最接近的近似，不等价：buf 的'档'是检查范围，不是方向",
        "buf_note": "full 要求两个方向都成立，buf 没有方向概念",
    },
    {
        "policy": "none",
        "buf_tier": "—",
        "relation": "buf 无'只列差异不判定'档",
        "buf_note": "本档只输出差异与证据，verdict 恒 compatible",
    },
)


def resolve_policy(name, history=None):
    """校验 policy 与 ``--history`` 的组合；不合规抛 :class:`UsageError`（退出码 2）。

    ``*-transitive`` 缺 ``--history`` **必须拒绝**——降级为单版本会把"与历史不兼容"
    静默报成"兼容"，这正是本工具要消除的误判。
    """
    if name not in POLICIES:
        raise UsageError("未知 policy: %r（允许 %s）" % (name, ", ".join(POLICIES)))
    versions = list(history or ())
    if name in TRANSITIVE and not versions:
        raise UsageError("%s 需要 --history（至少一个历史版本文件）；不降级为单版本比较" % name)
    if name not in TRANSITIVE and versions:
        raise UsageError("%s 不接受 --history（只有 *-transitive 档使用历史版本）" % name)
    return name


def mapping_table():
    """返回 buf 四档映射表的行 + 总声明，供 ``--explain-mapping`` 渲染。"""
    return {"notes": MAPPING_NOTES, "rows": [dict(row) for row in _MAPPING_ROWS]}


def diff(old_ir, new_ir):
    raise NotImplementedError("差异项产出（方向判定）计划在 M3 落地；当前为 M0 骨架")


def judge(differences, policy, history=()):
    raise NotImplementedError("七档 verdict 汇总计划在 M3 落地；当前为 M0 骨架")
