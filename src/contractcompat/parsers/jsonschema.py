# -*- coding: utf-8 -*-
"""JSON Schema 解析器：``properties`` / ``required`` / ``type`` / ``enum`` / ``oneOf`` / 可解析 ``$ref``。

**不可表达构造必须落 ``ir_unsupported``**（``patternProperties`` / ``if`` / ``then`` / ``else`` /
``dependentSchemas`` / ``dependentRequired`` / ``propertyNames`` / 递归 ``$ref``），带上
``json_pointer`` 与 ``reason``——这是对 getsentry/json-schema-diff 自述
"a lot of JSON Schema features are not implemented and therefore ignored" 的直接回应。

``$ref`` 只在**同文件内**解析（``#/definitions/...`` / ``#/$defs/...``）；外部 URL 一律不取
（零网络是红线），记为 ``external_ref``。环引用**不展开**（会栈溢出），记为 ``recursive_ref``。

指针纪律：所有 ``json_pointer`` 都是**相对文档根**的绝对指针。跟随 ``$ref`` 时不重置指针
（重置会让同一个构造在两条路径下报出两个不同的位置）。
"""

from __future__ import absolute_import

import json

from ..errors import SchemaParseError
from ..ir import ContractIR, EnumValue, Field, Unsupported

__all__ = [
    "parse_schema",
    "load_document",
    "UNSUPPORTED_CONSTRUCTS",
    "resolve_pointer",
    "walk_unsupported",
]

#: 首期**不可表达**的构造：见到就必须进 ``ir_unsupported``，不得静默忽略。
UNSUPPORTED_CONSTRUCTS = (
    "patternProperties",
    "if",
    "then",
    "else",
    "dependentSchemas",
    "dependentRequired",
    "propertyNames",
    "recursive_ref",
)

#: 这些键只有在条件分支建模下才有意义；出现即未建模（单独出现也算）。
_CONDITIONAL_KEYS = ("if", "then", "else")

#: 直接登记为不可表达的键（不需要再往下走）。
_UNMODELLED_KEYS = ("patternProperties", "dependentSchemas", "dependentRequired", "propertyNames")


def load_document(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            document = json.load(handle)
        except ValueError as error:
            raise SchemaParseError("JSON Schema 不是合法 JSON: %s（%s）" % (path, error))
    if not isinstance(document, dict):
        raise SchemaParseError("JSON Schema 顶层必须是对象: %s" % path)
    return document


def _escape(token):
    """JSON Pointer 转义（RFC 6901）：``~`` → ``~0``、``/`` → ``~1``。"""
    return str(token).replace("~", "~0").replace("/", "~1")


def _join(pointer, token):
    return "%s/%s" % (pointer, _escape(token))


def resolve_pointer(document, ref):
    """解析同文件内的 ``#/...`` 指针；不是本地指针或走不通时返回 ``None``。"""
    if not isinstance(ref, str) or not ref.startswith("#"):
        return None
    pointer = ref[1:]
    if pointer in ("", "/"):
        return document
    if not pointer.startswith("/"):
        return None
    node = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list):
            try:
                node = node[int(token)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return node


def _refs_in(node):
    """收集一个子树里所有 ``$ref`` 字符串（环检测用，不关心位置）。"""
    found = []
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            found.append(node["$ref"])
        for value in node.values():
            found.extend(_refs_in(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_refs_in(item))
    return found


def _is_recursive(ref, document, chain=()):
    """``ref`` 是否（经任意条 ref 链）回到 ``ref`` 自己。"""
    if ref in chain:
        return True
    target = resolve_pointer(document, ref)
    if target is None:
        return False
    for child in _refs_in(target):
        if _is_recursive(child, document, tuple(chain) + (ref,)):
            return True
    return False


def walk_unsupported(node, document, pointer="", out=None):
    """递归扫描不可表达构造，返回 ``[Unsupported]``。

    **存在即登记**：不因为"这个键可能不重要"跳过——静默忽略正是要避免的失败模式。
    ``$ref`` 的目标**不在这里跟随**：``$defs`` / ``definitions`` 子树本来就会被遍历到，
    重复跟随会让同一构造报两次。
    """
    out = [] if out is None else out
    if isinstance(node, list):
        for index, item in enumerate(node):
            walk_unsupported(item, document, "%s/%d" % (pointer, index), out)
        return out
    if not isinstance(node, dict):
        return out

    for key in _UNMODELLED_KEYS:
        if key in node:
            out.append(
                Unsupported(
                    key,
                    _join(pointer, key),
                    "首期 IR 不建模 %s：无法在不做正则/依赖求解的前提下枚举其语义" % key,
                )
            )

    for key in _CONDITIONAL_KEYS:
        if key in node:
            out.append(
                Unsupported(
                    key,
                    _join(pointer, key),
                    "首期 IR 不建模 if/then/else 条件分支：需要约束求解，且会破坏「同一输入同一结论」的确定性",
                )
            )
            break  # 一组 if/then/else 记一条就够，不刷屏

    ref = node.get("$ref")
    if isinstance(ref, str):
        if resolve_pointer(document, ref) is None:
            out.append(
                Unsupported(
                    "external_ref",
                    _join(pointer, "$ref"),
                    "引用 %r 不在本文件内或无法解析；零网络是红线，不取外部" % (ref,),
                )
            )
        elif _is_recursive(ref, document):
            out.append(
                Unsupported(
                    "recursive_ref",
                    _join(pointer, "$ref"),
                    "自引用/环引用 %r：不展开（会栈溢出），按不可表达登记" % (ref,),
                )
            )

    for name in sorted(node.get("properties") or {}):
        walk_unsupported(node["properties"][name], document, _join(_join(pointer, "properties"), name), out)

    items = node.get("items")
    if isinstance(items, dict):
        walk_unsupported(items, document, _join(pointer, "items"), out)
    elif isinstance(items, list):
        for index, child in enumerate(items):
            walk_unsupported(child, document, "%s/items/%d" % (pointer, index), out)

    for key in ("oneOf", "anyOf", "allOf"):
        branches = node.get(key)
        if isinstance(branches, list):
            for index, child in enumerate(branches):
                walk_unsupported(child, document, "%s/%s/%d" % (pointer, key, index), out)

    for key in ("definitions", "$defs"):
        for name in sorted(node.get(key) or {}):
            walk_unsupported(node[key][name], document, _join(_join(pointer, key), name), out)

    return out


def _literal_label(value):
    """enum 取值的确定性字面量标签（**不经 ``json.dumps``**：序列化单点在 canonical.py）。"""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[%s]" % ",".join(_literal_label(item) for item in value)
    if isinstance(value, dict):
        return "{%s}" % ",".join(
            "%s:%s" % (key, _literal_label(value[key])) for key in sorted(value)
        )
    return str(value)


def _deref(schema, document):
    """沿 ``$ref`` 链解引用一次（只用于取 ``type`` / ``enum`` 这类同层信息）。

    走不通或成环时返回 ``(None, ref)``，由调用方把字段类型标成未解析——
    「不可表达」已在 ``walk_unsupported`` 里登记，这里不重复抛错。
    """
    current = schema
    chain = ()
    while isinstance(current, dict) and isinstance(current.get("$ref"), str):
        ref = current["$ref"]
        if ref in chain:
            return None, ref
        chain += (ref,)
        current = resolve_pointer(document, ref)
        if current is None:
            return None, ref
    if not isinstance(current, dict):
        return None, None
    return current, None


def _type_label(raw, document, depth=0):
    """把字段的 ``type`` 压成确定性字符串；union 语义保留**分支集合与顺序**。"""
    if depth > 8:  # 深度保护：嵌套 combinator 不应无限展开
        return "too_deep"
    resolved, broken = _deref(raw, document)
    if broken is not None or resolved is None:
        return "unresolved_ref"

    for key in ("oneOf", "anyOf"):
        branches = resolved.get(key)
        if isinstance(branches, list):
            return "%s(%s)" % (
                key,
                ",".join(_type_label(branch, document, depth + 1) for branch in branches),
            )

    all_of = resolved.get("allOf")
    if isinstance(all_of, list) and len(all_of) == 1:
        return _type_label(all_of[0], document, depth + 1)

    kind = resolved.get("type")
    if isinstance(kind, list):
        return "union(%s)" % ",".join(str(item) for item in kind)
    if kind is None:
        if resolved.get("properties"):
            return "object"
        if "items" in resolved:
            return "array"
        return "any"
    label = str(kind)
    fmt = resolved.get("format")
    if fmt:
        label = "%s(%s)" % (label, fmt)
    return label


def _enum_values_of(raw, document):
    """``enum`` → ``EnumValue``（JSON Schema 无编号，``number`` 恒 ``None``）。"""
    resolved, broken = _deref(raw, document)
    if broken is not None or resolved is None:
        return ()
    values = resolved.get("enum")
    if not isinstance(values, list):
        return ()
    return tuple(EnumValue(_literal_label(value), None) for value in values)


def _oneof_membership(raw, document):
    """``oneOf`` / ``anyOf`` 存在时记下分支签名（R6 的证据面）。

    签名用"分支的 type 标签"而不是下标：下标一动就全变，会把「同一个分支换了位置」
    误报成「分支移动」——而 oneOf 的分支顺序在语义上无关。
    """
    resolved, broken = _deref(raw, document)
    if broken is not None or resolved is None:
        return None
    for key in ("oneOf", "anyOf"):
        branches = resolved.get(key)
        if isinstance(branches, list) and branches:
            labels = sorted(_type_label(branch, document, 1) for branch in branches)
            return "%s:%s" % (key, ",".join(labels))
    return None


def _additional_properties(root):
    value = root.get("additionalProperties")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return "schema"


def parse_schema(path, require_complete_ir=False):
    """JSON Schema → :class:`ContractIR`（顶层 ``properties`` 收成字段）。

    不可表达构造**不抛错**（是否因此拒绝出结论是 ``--require-complete-ir`` 的策略，
    由 CLI 统一判），而是进 ``ir_unsupported``，让报告显式列出。
    """
    document = load_document(path)

    unsupported = walk_unsupported(document, document, "")

    # 顶层 $ref → 解析到真正的对象 schema 再取 properties
    root, broken = _deref(document, document)
    if broken is not None or root is None:
        root = document

    properties = root.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    required = root.get("required")
    required_names = set(required) if isinstance(required, list) else set()

    fields = []
    for name in sorted(properties):
        raw = properties[name]
        if not isinstance(raw, dict):
            raise SchemaParseError("properties/%s 必须是对象: %s" % (name, path))
        resolved, ref_broken = _deref(raw, document)
        if ref_broken is not None or resolved is None:
            resolved = {}  # 引用走不通：已由 walk_unsupported 记成 external_ref

        has_default = "default" in resolved
        fields.append(
            Field(
                name=name,
                type=_type_label(raw, document),
                cardinality="required" if name in required_names else "optional",
                number=None,
                json_pointer="/properties/%s" % _escape(name),
                default_present=has_default,
                default_value=resolved.get("default"),
                enum_values=_enum_values_of(raw, document),
                oneof_membership=_oneof_membership(raw, document),
                aliases=(),
            )
        )

    return ContractIR(
        "jsonschema",
        name=str(root.get("title") or ""),
        fields=fields,
        reserved_numbers=(),
        reserved_names=(),
        ir_unsupported=unsupported,
        meta={
            "additional_properties": _additional_properties(root),
            "required": sorted(required_names),
            "field_count": len(fields),
            "schema_dialect": str(document.get("$schema") or ""),
        },
    )
