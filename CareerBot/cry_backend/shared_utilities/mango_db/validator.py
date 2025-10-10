from __future__ import annotations
import json
import os
from typing import Any, Dict, List


def _load_collection_spec_file(collection: str) -> Dict[str, Any]:
    """
    _load_collection_spec_file(collection) 读取单集合 JSON（collections_{collection}_info.json）
    返回解析后的字典对象，用于校验该集合字段与操作白名单
    """
    here = os.path.dirname(__file__)
    fname = f"collections_{collection}_info.json"
    cfg_path = os.path.join(here, fname)
    if not os.path.exists(cfg_path):
        raise ValueError(f"Collection spec json not found: {fname}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_collection_spec(collection: str) -> Dict[str, Any]:
    """
    _get_collection_spec(collection) 返回指定集合的配置对象
    直接读取该集合的独立 JSON 文件
    """
    spec = _load_collection_spec_file(collection)
    if not isinstance(spec, dict):
        raise ValueError(f"Invalid spec for collection: {collection}")
    return spec


def _flatten_doc_paths(doc: Dict[str, Any], prefix: str = "") -> List[str]:
    """
    _flatten_doc_paths(doc, prefix) 展开文档所有叶子路径（点分隔）
    数组项不展开索引，仅保留字段名（用于宽松校验）
    """
    paths: List[str] = []
    for k, v in (doc or {}).items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            paths.extend(_flatten_doc_paths(v, key))
        elif isinstance(v, list):
            # 不展开索引，保留数组字段路径
            paths.append(key)
        else:
            paths.append(key)
    return paths


def _allowed_field_paths(spec: Dict[str, Any]) -> List[str]:
    """
    _allowed_field_paths(spec) 解析 fields 映射中的所有字段路径
    - spec.fields: { path: type }；type 末尾 '?' 表示可选
    - 返回全部字段路径列表
    """
    fields = spec.get("fields") or {}
    return list(fields.keys())


def _is_field_allowed(field_path: str, allowed: List[str]) -> bool:
    """
    _is_field_allowed(field_path, allowed) 判断字段是否在白名单中
    规则：
    - 完全匹配直接通过
    - 若字段形如 a.b.$.c，则允许 a.b[].c 或 a.b[].*.c 的等价表示方式（简化：a.b[] 存在即允许 a.b.$.*）
    - 若字段形如 a.b.c，但白名单有 a.b[]，则仅用于 push，不用于 set（需调用者按语义区别）
    """
    if field_path in allowed:
        return True
    # 支持 positional $ 场景：如 email_verification.history.$.used
    if ".$." in field_path:
        base, rest = field_path.split(".$.", 1)
        # 允许基于声明的数组子字段匹配，例如 fields 中存在 email_verification.history[].used
        candidate = f"{base}[].{rest}"
        if candidate in allowed:
            return True
    return False


def _has_required_paths(doc: Dict[str, Any], required: List[str]) -> bool:
    """
    _has_required_paths(doc, required) 判断文档是否包含所有必填路径
    支持点路径（如 profile.email）
    """
    for path in required:
        # 数组必填由业务场景决定，此处仅检查非数组路径
        if path.endswith("[]"):
            # 对 insert 不强制数组字段必填
            continue
        if not _path_exists(doc, path):
            return False
    return True


def _path_exists(doc: Dict[str, Any], path: str) -> bool:
    """
    _path_exists(doc, path) 判断点路径是否存在于文档中
    """
    cur: Any = doc
    for seg in path.split("."):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return False
    return True


def validate_insert(collection: str, document: Dict[str, Any]) -> None:
    """
    validate_insert(collection, document) 校验插入文档
    - 检查必填字段（点路径）存在
    - 可选：可扩展为严格白名单（当前宽松，允许多余字段）
    """
    spec = _get_collection_spec(collection)
    required = spec.get("required") or []
    if not _has_required_paths(document, required):
        raise ValueError(f"Insert missing required fields for {collection}")
    allow_extra = bool(spec.get("allow_extra", False))
    if not allow_extra:
        # 校验不存在非声明字段
        allowed = set(_allowed_field_paths(spec))
        for path in _flatten_doc_paths(document):
            if path not in allowed:
                # 容忍对象聚合字段（如将来引入），当前严格按叶子字段
                raise ValueError(f"Insert field not allowed: {collection}.{path}")


def validate_update_set(collection: str, set_payload: Dict[str, Any]) -> None:
    """
    validate_update_set(collection, set_payload) 校验 $set 负载
    - 检查操作允许
    - 检查字段均在 allowed 字段白名单（支持 $. 简化）
    """
    spec = _get_collection_spec(collection)
    allowed_ops: List[str] = spec.get("allowed_ops") or []
    if "update.$set" not in allowed_ops:
        raise ValueError(f"$set not allowed for {collection}")
    allowed_fields = _allowed_field_paths(spec)
    for key in (set_payload or {}).keys():
        if not _is_field_allowed(key, allowed_fields):
            raise ValueError(f"Field not allowed for $set: {collection}.{key}")


def validate_push(collection: str, push_payload: Dict[str, Any]) -> None:
    """
    validate_push(collection, push_payload) 校验 $push 负载
    - 仅允许 JSON 中列出的 update.$push(xxx) 操作（逐键检查）
    """
    spec = _get_collection_spec(collection)
    allowed_ops: List[str] = spec.get("allowed_ops") or []
    # 推断为声明的数组路径集合，例如 email_verification.history[]
    array_paths = {
        k[:-2] for k in (spec.get("fields") or {}).keys() if k.endswith("[]")
    }
    for key in (push_payload or {}).keys():
        op_sig = f"update.$push({key})"
        if op_sig not in allowed_ops:
            raise ValueError(f"$push not allowed for {collection}.{key}")
        # 仅允许针对数组字段 push
        if key not in array_paths:
            raise ValueError(f"$push target must be an array field: {collection}.{key}")


def validate_set_on_insert(collection: str, soi_payload: Dict[str, Any]) -> None:
    """
    validate_set_on_insert(collection, soi_payload) 校验 $setOnInsert 文档
    - 宽松校验：若提供 user_id 等主键，允许 upsert
    - 可扩展：按 required_fields 检查首次写入必填
    """
    spec = _get_collection_spec(collection)
    required = spec.get("required") or []
    # $setOnInsert 仅在 upsert 首次写入时完整文档生效，此处不强制全部必填
    # 但至少应包含主键（若配置了）
    main_keys = [k for k in required if "." not in k and not k.endswith("[]")]
    for mk in main_keys:
        if mk not in soi_payload:
            # 不强制报错，交由上游 filter+upsert 判断；保持宽松
            return
    return


