# -*- coding: utf-8 -*-
"""规范 JSON 序列化、digest 与 ``--verify`` 的定位逻辑。

**全仓唯一允许调用 ``json.dumps`` 的地方**（测试有守门断言）——多个入口各写一份
序列化参数，迟早出现"一个带 BOM 一个不带 / 一个 sort_keys 一个不排"的跨机漂移。

冻结契约（改动会打挂所有 golden）：
  * ``sort_keys=True``、``ensure_ascii=False``、``indent=2``
  * 换行一律 ``\\n``、结尾恰好一个换行
  * ``digest`` = sha256(去掉顶层 ``digest`` 键后的规范字节) 的小写十六进制
"""

from __future__ import absolute_import

import hashlib
import json

from .errors import CanonicalError

__all__ = [
    "DIGEST_KEY",
    "dumps",
    "loads",
    "digest",
    "body_of",
    "verify_report",
    "structural_diff",
]

DIGEST_KEY = "digest"


def dumps(obj):
    """序列化为规范 JSON 文本（含结尾换行）。"""
    try:
        text = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as error:
        raise CanonicalError("对象无法序列化为 JSON: %s" % error)
    return text + "\n"


def loads(text):
    """严格解析 JSON 文本；顶层必须是对象。"""
    try:
        obj = json.loads(text)
    except ValueError as error:
        raise CanonicalError("不是合法 JSON: %s" % error)
    if not isinstance(obj, dict):
        raise CanonicalError("报告顶层必须是 JSON 对象，实际是 %s" % type(obj).__name__)
    return obj


def body_of(report):
    """返回去掉顶层 ``digest`` 键的新对象（不修改入参）。"""
    return dict((key, value) for key, value in report.items() if key != DIGEST_KEY)


def digest(report):
    """计算规范 digest：对"体内"内容取 sha256。

    先剥 ``digest`` 再算，否则"写回 digest"这个动作会改变 digest 本身（自指）。
    """
    return hashlib.sha256(dumps(body_of(report)).encode("utf-8")).hexdigest()


def structural_diff(expected, actual, path=""):
    """深比对两个 JSON 值，返回 ``[{json_path, expected, actual}]``。

    ``json_path`` 用 ``a.b[0].c`` 形态（与 ``--verify`` 的定位输出一致）；
    只用 diff 的第一层差异——目的不是给出完整补丁，而是"哪一处被改了"。
    """
    differences = []
    _diff_into(expected, actual, path, differences)
    return differences


def _diff_into(expected, actual, path, out):
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            child = "%s.%s" % (path, key) if path else key
            if key not in actual:
                out.append({"json_path": child, "expected": expected[key], "actual": None, "kind": "missing"})
            elif key not in expected:
                out.append({"json_path": child, "expected": None, "actual": actual[key], "kind": "unexpected"})
            else:
                _diff_into(expected[key], actual[key], child, out)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            out.append({"json_path": path, "expected": len(expected), "actual": len(actual), "kind": "length"})
        for index in range(min(len(expected), len(actual))):
            _diff_into(expected[index], actual[index], "%s[%d]" % (path, index), out)
        return
    if expected != actual:
        out.append({"json_path": path, "expected": expected, "actual": actual, "kind": "value"})


def verify_report(report, baseline=None):
    """校验报告未被篡改。

    * ``baseline`` 为 None：只做**自洽校验**（重算 digest 与报告里写的一致）。
      这条路能抓住"有人手改了内容但没重算 digest"。
    * 给了 ``baseline``：**先比内容再比 digest**——先算 digest 会把"哪一处被改了"盖掉。
      返回的差异列表定位到叶子字段（``findings[3].severity`` 形态）。

    返回 ``(ok, differences)``；``differences`` 为空即一致。
    """
    differences = []
    if baseline is not None:
        differences = structural_diff(body_of(baseline), body_of(report))
        if differences:
            return False, differences
    recorded = report.get(DIGEST_KEY)
    recomputed = digest(report)
    if recorded != recomputed:
        return False, [
            {
                "json_path": DIGEST_KEY,
                "expected": recomputed,
                "actual": recorded,
                "kind": "digest",
                "hint": "内容与登记值不匹配：先看其他差异项，再看本项",
            }
        ]
    return True, []
