# -*- coding: utf-8 -*-
"""归因（"谁会炸"）+ 修复动作。

归因只由三元组决定：``(direction 判定, deploy_order, 该格式的字段可寻址性)``
（``data/README.md`` §4.6）。**不给 ``--deploy-order`` 时 ``blast_radius`` 是 null**，
``notes`` 写 ``deploy_order_not_given``——不猜、不给默认顺序。

``--deploy-order`` 的四个取值各自对应 §4.6 的一行场景（"版本偏差横在哪一侧"）：

  * ``consumers-first`` → ``OLD_CONSUMER``：老消费者仍是线上版本，读到新生产者写出的数据；
  * ``producers-first`` → ``NEW_CONSUMER``：新消费者已上线，还在读老生产者写出的数据；
  * ``simultaneous``   → ``BOTH``：两侧版本同时在位，两个方向都暴露；
  * ``replay``         → ``REPLAY_ONLY``：只有历史数据重放时炸，实时流量不炸。

**``REPLAY_ONLY`` 只在显式 ``replay`` 时出现**（不默认推断）：历史重放不是"另一种发布
顺序"，它是一个显式的验证动作。

``direction`` 是规则层已带上的事实（本层**不重算方向**）：N/A 行（``severity=None``）
不参与归因，``blast_radius`` 保持 ``null``——"该格式没有这个概念"不是"没人会炸"。

``repair_action`` / ``repair_hint`` 由规则层填好（带可执行落点），归因层**只补
``blast_radius``**，不覆盖任何已有结论。
"""

from __future__ import absolute_import

from .errors import UsageError

__all__ = [
    "DEPLOY_ORDERS",
    "BLAST_RADII",
    "REPAIR_ACTIONS",
    "NOT_GIVEN_NOTE",
    "ADDRESSABILITY",
    "validate_deploy_order",
    "attribute",
]

DEPLOY_ORDERS = ("consumers-first", "producers-first", "simultaneous", "replay")

BLAST_RADII = ("OLD_CONSUMER", "NEW_CONSUMER", "BOTH", "REPLAY_ONLY")

REPAIR_ACTIONS = ("reserve", "alias", "add-default", "add-branch", "bump-and-version")

#: 缺 ``--deploy-order`` 时写进 ``notes`` 的固定串（不是提示语，是结论的一部分）。
NOT_GIVEN_NOTE = "deploy_order_not_given"

#: 三元组的第三维：该格式的字段可寻址性（``data/README.md`` §4.6 点名的三种）。
#: 三格式都"可按名/号寻址"，所以这一维在当前规则集下不改变四态分配；
#: 它仍显式参与归因：**不认识的格式不归因**（不猜一个可寻址性）。
ADDRESSABILITY = {
    "proto": "field-number",        # 按字段号；未知字段号可跳过
    "avro": "field-name-alias",     # 按字段名 + alias
    "jsonschema": "property-name",  # 按属性名；未知属性默认容忍
}

#: 部署顺序 → 版本偏差落在谁身上（§4.6 四行的直译）。
_RADIUS_BY_ORDER = {
    "consumers-first": "OLD_CONSUMER",
    "producers-first": "NEW_CONSUMER",
    "simultaneous": "BOTH",
    "replay": "REPLAY_ONLY",
}


def validate_deploy_order(order):
    if order is None:
        return None
    if order not in DEPLOY_ORDERS:
        raise UsageError("未知 deploy-order: %r（允许 %s）" % (order, ", ".join(DEPLOY_ORDERS)))
    return order


def _format_is_addressable(row):
    """finding 的输入格式是否在 ``ADDRESSABILITY`` 里（三元组第三维的输入面）。"""
    evidence = row.get("evidence") or {}
    return evidence.get("format") in ADDRESSABILITY


def attribute(findings, deploy_order=None):
    """为每条命中填 ``blast_radius``；返回 ``(findings, notes)``。

    * 缺 ``deploy_order`` → 一律留 ``null`` + ``notes=["deploy_order_not_given"]``；
    * N/A 行（``severity is None``）→ 留 ``null``，不参与归因；
    * 命中行 → 按部署顺序填四态之一；格式不可寻址时不猜（留 ``null`` + 说明）。
    """
    validate_deploy_order(deploy_order)
    # 键面补齐是归因层的职责：规则层输出**只缺 blast_radius**（K4），本层补上（哪怕是 None），
    # 补完每条命中才与 report.FINDING_KEYS 完全一致。
    for row in findings:
        if "blast_radius" not in row:
            row["blast_radius"] = None
    if deploy_order is None:
        # 语义已定：归因字段留 null 并显式说明，**不替用户挑一个默认顺序**
        return findings, [NOT_GIVEN_NOTE]

    notes = []
    for row in findings:
        if row.get("severity") is None:
            continue  # N/A 是"该格式无此概念"，不是"没人会炸"
        if not _format_is_addressable(row):
            notes.append("format_not_addressable")
            continue
        row["blast_radius"] = _RADIUS_BY_ORDER[deploy_order]
    # 同一条说明只留一次（多条不可寻址的 finding 不重复刷屏）
    deduped = []
    for note in notes:
        if note not in deduped:
            deduped.append(note)
    return findings, deduped
