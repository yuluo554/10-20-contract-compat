# -*- coding: utf-8 -*-
"""归因四态与 deploy-order 契约（M0 已实现的部分）。

M5 会接上真实映射；这里先锁住"缺省不猜"与"未知顺序拒绝"——两条都是题面红线。
"""

import pytest

from contractcompat.blast import (
    BLAST_RADII,
    DEPLOY_ORDERS,
    NOT_GIVEN_NOTE,
    REPAIR_ACTIONS,
    attribute,
    validate_deploy_order,
)
from contractcompat.errors import UsageError


def test_four_deploy_orders():
    assert set(DEPLOY_ORDERS) == {"consumers-first", "producers-first", "simultaneous", "replay"}


def test_four_blast_radii():
    assert set(BLAST_RADII) == {"OLD_CONSUMER", "NEW_CONSUMER", "BOTH", "REPLAY_ONLY"}


def test_five_repair_actions():
    assert set(REPAIR_ACTIONS) == {"reserve", "alias", "add-default", "add-branch", "bump-and-version"}


def test_unknown_deploy_order_rejected():
    with pytest.raises(UsageError):
        validate_deploy_order("consumers-last")


def test_none_deploy_order_is_allowed():
    assert validate_deploy_order(None) is None


def test_missing_deploy_order_does_not_guess():
    """不给 --deploy-order 时归因字段留 null 并显式说明——**不替用户挑一个默认顺序**。

    默认值会被当成结论用，而这正是本题要消除的误判。
    """
    findings = [{"rule_id": "R1", "stable_path": "6", "blast_radius": None}]
    result, notes = attribute(findings, None)
    assert result[0]["blast_radius"] is None
    assert NOT_GIVEN_NOTE in notes


def test_given_deploy_order_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        attribute([{"rule_id": "R1"}], "consumers-first")
