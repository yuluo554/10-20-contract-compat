# -*- coding: utf-8 -*-
"""归因（"谁会炸"）+ 修复动作。

归因只由三元组决定：``(direction 判定, deploy_order, 该格式的字段可寻址性)``
（``data/README.md`` §4.6）。**不给 ``--deploy-order`` 时 ``blast_radius`` 是 null**，
``notes`` 写 ``deploy_order_not_given``——不猜、不给默认顺序。

M0 骨架：``DEPLOY_ORDERS`` / ``BLAST_RADII`` / ``attribute`` 的契约与拒绝路径已实现；
真正映射表留 M5。
"""

from __future__ import absolute_import

from .errors import UsageError

__all__ = [
    "DEPLOY_ORDERS",
    "BLAST_RADII",
    "REPAIR_ACTIONS",
    "NOT_GIVEN_NOTE",
    "validate_deploy_order",
    "attribute",
]

DEPLOY_ORDERS = ("consumers-first", "producers-first", "simultaneous", "replay")

BLAST_RADII = ("OLD_CONSUMER", "NEW_CONSUMER", "BOTH", "REPLAY_ONLY")

REPAIR_ACTIONS = ("reserve", "alias", "add-default", "add-branch", "bump-and-version")

#: 缺 ``--deploy-order`` 时写进 ``notes`` 的固定串（不是提示语，是结论的一部分）。
NOT_GIVEN_NOTE = "deploy_order_not_given"


def validate_deploy_order(order):
    if order is None:
        return None
    if order not in DEPLOY_ORDERS:
        raise UsageError("未知 deploy-order: %r（允许 %s）" % (order, ", ".join(DEPLOY_ORDERS)))
    return order


def attribute(findings, deploy_order=None):
    """为每条 finding 填 ``blast_radius`` / ``repair_action`` / 说明；返回 (findings, notes)。"""
    validate_deploy_order(deploy_order)
    if deploy_order is None:
        # 语义已定：归因字段留 null 并显式说明，**不替用户挑一个默认顺序**
        notes = [NOT_GIVEN_NOTE]
        return findings, notes
    raise NotImplementedError("归因映射（四态 × 部署顺序）计划在 M5 落地；当前为 M0 骨架")
