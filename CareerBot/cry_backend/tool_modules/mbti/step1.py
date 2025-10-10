#!/usr/bin/env python3  # 指定Python3解释器运行这个脚本
# -*- coding: utf-8 -*-  # 声明文件使用UTF-8编码，支持中文字符
"""
step1.py - MBTI测试引导处理器（流程驱动版本）
MBTI测试第一步：接收用户请求，创建request_id，写入用户状态为ongoing，返回英文测试引导信息
按照hub/flow_example.py标准实现流程上下文支持和状态管理
"""

from typing import Dict, Union, Any
from pathlib import Path  # 导入类型提示，支持流程上下文字段
import json
import re
import sys  # 导入sys模块，用于路径操作
import os  # 导入os模块，用于路径操作

# 添加上级目录到Python路径，以便导入shared_utilities和hub模块
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# Time 通过绝对导入路径shared_utilities.time.Time获取，用于生成带时间戳的request ID
from shared_utilities.time import Time

# DatabaseOperations 通过绝对导入路径shared_utilities.mongodb_connector.DatabaseOperations获取
# 用于执行数据库写入操作，设置用户MBTI测试状态
from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from pymongo.errors import PyMongoError

# ======== Strong request/response models (Pydantic) ========
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username
from .errors import MBTIConfigurationError, MBTIStepStateError


class Step1Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., description="timestamp_uuidv4 request id")
    user_id: str = Field(..., min_length=1, description="user id")
    auth_username: str = Field(default="", description="Auth username accompanying the user id")
    flow_id: str = Field(default="mbti_personality_test")

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)


# ======== Batch-based MBTI form generation & answer ingestion ========
from typing import List


class BatchFormRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., description="timestamp_uuidv4 request id")
    user_id: str = Field(..., description="user id")
    flow_id: str = Field(default="mbti_personality_test", description="MBTI flow identifier")

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")


class BatchAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    user_id: str
    flow_id: str = Field(default="mbti_personality_test")
    batch: int = Field(..., ge=1, le=8)
    question_id: str
    answer: str
    message_id: str | None = None

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("question_id")
    def _validate_qid(cls, value: str) -> str:
        if not re.match(r'^q_\d+_\d+$', value):
            raise ValueError("Invalid question_id format")
        return value

    @field_validator("answer")
    def _validate_answer(cls, value: str) -> str:
        if value not in {"1", "2", "3", "4", "5"}:
            raise ValueError("Invalid likert score")
        return value


_QUESTION_BANK_CACHE: List[Dict[str, Any]] = []
_CACHE_LOADED: bool = False


def _load_question_bank() -> List[Dict[str, Any]]:
    global _QUESTION_BANK_CACHE, _CACHE_LOADED
    if _CACHE_LOADED and _QUESTION_BANK_CACHE:
        return _QUESTION_BANK_CACHE

    file_path = Path(__file__).with_name('step1_mbti_questions.json')
    try:
        raw = json.loads(file_path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise MBTIConfigurationError(f"Unable to load MBTI question bank: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MBTIConfigurationError("MBTI question bank JSON is invalid") from exc

    if isinstance(raw, dict):
        questions = raw.get('mbti_questions') or raw.get('questions')
    else:
        questions = raw

    if not isinstance(questions, list):
        raise MBTIConfigurationError("MBTI question bank must be a list of questions")

    _QUESTION_BANK_CACHE = list(questions)
    _CACHE_LOADED = True
    return _QUESTION_BANK_CACHE


def _get_batch_questions(batch_number: int) -> List[Dict[str, Any]]:
    questions = _load_question_bank()
    if not questions:
        raise MBTIConfigurationError("Question bank is empty")
    offset = (batch_number - 1) * 12
    size = 12
    batch_slice = questions[offset:offset + size]
    if not batch_slice:
        raise MBTIConfigurationError(f"No questions available for batch {batch_number}")
    return batch_slice


def _build_batch_form_schema(questions: List[Dict[str, Any]], batch_number: int) -> Dict[str, Any]:
    if not questions:
        raise MBTIConfigurationError("Question bank returned no entries for batch")

    form_fields: List[Dict[str, Any]] = []
    for index, question in enumerate(questions):
        question_id = f"q_{batch_number}_{index + 1}"
        question_text = (
            question.get("mbti_questions_text")
            or question.get("text")
            or f"Question {index + 1}"
        )
        form_fields.append(
            {
                "field_id": question_id,
                "type": "radio",
                "label": question_text,
                "required": True,
                "options": [
                    {"value": "1", "label": "Strongly Disagree"},
                    {"value": "2", "label": "Disagree"},
                    {"value": "3", "label": "Neutral"},
                    {"value": "4", "label": "Agree"},
                    {"value": "5", "label": "Strongly Agree"},
                ],
            }
        )

    return {
        "form_id": f"mbti_batch_{batch_number}",
        "title": f"MBTI Assessment - Batch {batch_number}/8",
        "description": f"Please answer all questions in batch {batch_number}. There are {len(questions)} questions in this batch.",
        "fields": form_fields,
        "submit_button": {
            "text": "Submit Batch" if batch_number < 8 else "Complete Assessment",
            "step_id": f"mbti_batch_{batch_number}_submit",
        },
    }


def _count_batch_answers(user_id: str, flow_id: str, batch_number: int) -> int:
    docs = DatabaseOperations().find(
        "user_chathistory",
        {"user_id": user_id, "flow_id": flow_id, "batch": batch_number, "event_type": "mbti_answer"},
        {"_id": 1},
    )
    return len(docs or [])


def _assert_prev_batch_done(user_id: str, flow_id: str, batch_number: int) -> None:
    if batch_number <= 1:
        return
    prev_count = _count_batch_answers(user_id, flow_id, batch_number - 1)
    if prev_count < 12:
        raise MBTIStepStateError("Previous batch not completed")


def _expected_next_batch(user_id: str, flow_id: str) -> int:
    for i in range(1, 9):
        cnt = _count_batch_answers(user_id, flow_id, i)
        if cnt < 12:
            return i
    return 9


def _assert_batch_matches_expected(user_id: str, flow_id: str, batch_number: int) -> None:
    expected = _expected_next_batch(user_id, flow_id)
    if expected != batch_number:
        raise MBTIStepStateError(f"Invalid batch progression: expected {expected}, got {batch_number}")


def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}


async def _handle_batch(request: Dict[str, Any], batch_number: int) -> Dict[str, Any]:
    try:
        req = BatchFormRequest(**request)
    except ValidationError as exc:
        return {
            "success": False,
            "step_id": f"mbti_batch_{batch_number}",
            "error": exc.errors(),
            "error_type": "INVALID_INPUT",
        }

    request_id = req.request_id
    user_id = req.user_id
    flow_id = req.flow_id

    if _expected_next_batch(user_id, flow_id) == 9:
        return {
            "success": False,
            "step_id": f"mbti_batch_{batch_number}",
            "error": "Assessment already completed; please do not repeat.",
            "error_type": "STEP_ALREADY_COMPLETE",
        }

    try:
        _assert_prev_batch_done(user_id, flow_id, batch_number)
        _assert_batch_matches_expected(user_id, flow_id, batch_number)
        batch_questions = _get_batch_questions(batch_number)
        form_schema = _build_batch_form_schema(batch_questions, batch_number)
    except MBTIStepStateError as exc:
        return {
            "success": False,
            "step_id": f"mbti_batch_{batch_number}",
            "error": str(exc),
            "error_type": "CONFLICT",
        }
    except MBTIConfigurationError as exc:
        return {
            "success": False,
            "step_id": f"mbti_batch_{batch_number}",
            "error": str(exc),
            "error_type": "DEPENDENCY_ERROR",
        }

    return {
        "request_id": request_id,
        "user_id": user_id,
        "flow_id": flow_id,
        "success": True,
        "step": f"mbti_batch_{batch_number}",
        "message": f"MBTI Assessment Batch {batch_number}/8 - Please complete the form below.",
        "form_data": {
            "form_schema": form_schema,
            "form_id": f"mbti_batch_{batch_number}",
            "batch_info": {
                "current_batch": batch_number,
                "total_batches": 8,
                "questions_per_batch": 12,
                "total_questions": 96,
            },
        },
        "next_step": f"mbti_batch_{batch_number}_answer",
        "step_id": f"mbti_batch_{batch_number}",
    }


def _ingest_answer_event(req: BatchAnswerRequest) -> None:
    meta = {}
    if req.message_id:
        meta["message_id"] = req.message_id
    try:
        DatabaseOperations().update(
            "user_chathistory",
            {"user_id": req.user_id, "flow_id": req.flow_id, "batch": req.batch, "question_id": req.question_id, "event_type": "mbti_answer"},
            {
                "$setOnInsert": {"user_id": req.user_id, "flow_id": req.flow_id, "batch": req.batch, "question_id": req.question_id, "event_type": "mbti_answer"},
                "$set": {"answer": req.answer, "ts": Time.timestamp()},
                "$push": {"meta_history": meta},
            },
        )
    except PyMongoError as exc:
        raise MBTIDatabaseError(f"Failed to write MBTI answer: {exc}") from exc


async def _handle_batch_answer(request: Dict[str, Any], batch_number: int) -> Dict[str, Any]:
    try:
        req = BatchAnswerRequest(**request)
    except ValidationError as exc:
        return {"success": False, "error": exc.errors(), "error_type": "INVALID_INPUT"}

    if req.batch != batch_number:
        return {"success": False, "error": "batch mismatch", "error_type": "INVALID_INPUT"}
    if _expected_next_batch(req.user_id, req.flow_id) == 9:
        return {"success": False, "error": "Assessment already completed", "error_type": "STEP_ALREADY_COMPLETE"}

    try:
        _ingest_answer_event(req)
    except MBTIDatabaseError as exc:
        return {"success": False, "error": str(exc), "error_type": "DEPENDENCY_ERROR"}

    count = _count_batch_answers(req.user_id, req.flow_id, batch_number)
    return {
        "success": True,
        "request_id": req.request_id,
        "user_id": req.user_id,
        "flow_id": req.flow_id,
        "step": f"mbti_batch_{batch_number}_answer",
        "current_count": count,
        "required": 12,
        "batch_completed": count >= 12,
        "next_step": (
            f"mbti_batch_{batch_number+1}" if count >= 12 and batch_number < 8 else f"mbti_batch_{batch_number}"
        ),
    }


async def process(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MBTI step 1 entrypoint with strong validation and structured errors."""
    request = _get_envelope_data(envelope)
    try:
        req = Step1Request(**request)
    except ValidationError as exc:
        return {
            "request_id": request.get("request_id", "unknown") if isinstance(request, dict) else "unknown",
            "user_id": request.get("user_id") if isinstance(request, dict) else None,
            "flow_id": request.get("flow_id", "mbti_personality_test") if isinstance(request, dict) else "mbti_personality_test",
            "success": False,
            "step": "mbti_step1",
            "error": exc.errors(),
            "error_type": "INVALID_INPUT",
        }

    try:
        return await _handle_mbti_step_jump(req.request_id, req.user_id, req.flow_id, 1)
    except MBTIStepStateError as exc:
        return {
            "request_id": req.request_id,
            "user_id": req.user_id,
            "flow_id": req.flow_id,
            "success": False,
            "step": "mbti_step1",
            "error": str(exc),
            "error_type": "CONFLICT",
        }
    except MBTIConfigurationError as exc:
        return {
            "request_id": req.request_id,
            "user_id": req.user_id,
            "flow_id": req.flow_id,
            "success": False,
            "step": "mbti_step1",
            "error": str(exc),
            "error_type": "DEPENDENCY_ERROR",
        }

async def _handle_mbti_step_jump(request_id: str, user_id: str, flow_id: str, current_step: int) -> Dict[str, Any]:
    """
    _handle_mbti_step_jump 通过异步执行处理MBTI测试引导逻辑（流程驱动版本）
    根据步骤编号返回对应的测试引导信息和预设英文提示，包含流程上下文字段
    """
    # current_step 等于1时表示用户在MBTI第一步测试引导阶段
    # 返回包含request_id、user_id、flow_id、success状态和预设英文引导信息的字典
    if current_step == 1:
        return {
            "request_id": request_id,  # request_id 赋值给字典的request_id键，作为请求标识符
            "user_id": user_id,  # user_id 赋值给字典的user_id键，作为用户标识符
            "flow_id": flow_id,  # flow_id 赋值给字典的flow_id键，作为流程标识符
            "success": True,  # success 设置为True，表示处理成功
            "step": "mbti_step1",  # step 设置为字符串"mbti_step1"，标识当前步骤
            "message": "First, please complete the following scenario test so that we can better understand you. Please use the link below to access the test questions page.",  # message 赋值英文预设提示信息
            # 使用结构化按钮返回，前端通过 action 打开内置调查界面
            "buttons": [
                {
                    "id": "mbti_assessment", 
                    "text": "Take Test",
                    # icon removed to avoid emoji per code policy
                    "function_status": "DevComplete",
                    "data": {"step_id": "mbti_batch_1"}
                }
            ],
            "next_step": "mbti_step2",  # next_step 设置为字符串"mbti_step2"，表示下一步骤标识
            "current_mbti_step": current_step  # current_mbti_step 赋值当前步骤编号1
        }
    else:
        # current_step 不等于1时表示异常情况，不应该到达此分支
        # 返回包含错误信息的字典，标识处理失败和异常步骤
        return {
            "request_id": request_id,  # request_id 赋值给字典的request_id键，保持请求标识符
            "user_id": user_id,  # user_id 赋值给字典的user_id键，保持用户标识符
            "flow_id": flow_id,  # flow_id 赋值给字典的flow_id键，保持流程标识符
            "success": False,  # success 设置为False，表示处理失败
            "step": "error",  # step 设置为字符串"error"，标识错误步骤
            "message": f"Unexpected step in _handle_mbti_step_jump: {current_step}",  # message 赋值格式化字符串，包含异常步骤信息
            "error_code": "UNEXPECTED_STEP"  # error_code 设置为字符串"UNEXPECTED_STEP"，标识错误类型
        }


# ======== Module-local step specification (self-contained) ========
MBTI_STEP1_STEP_SPECS = {
    "steps": [
        {"step_id": "mbti_step1", "handler": "cry_backend.tool_modules.mbti.step1.process"},
        # 注册 8 个批次表单生成
        *[{"step_id": f"mbti_batch_{i}", "handler": f"cry_backend.tool_modules.mbti.step1.handle_mbti_batch_{i}"} for i in range(1, 9)],
        # 注册 8 个逐题作答事件写入
        *[{"step_id": f"mbti_batch_{i}_answer", "handler": f"cry_backend.tool_modules.mbti.step1.handle_mbti_batch_{i}_answer"} for i in range(1, 9)],
    ]
}
# MBTI_STEP1_STEP_SPECS(steps=[{step_id/handler}])
# 提供本步骤的自包含路由规范，供模块内 router 聚合

# ======== Public handlers for batches (wrappers) ========

async def handle_mbti_batch_1(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 1)

async def handle_mbti_batch_2(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 2)

async def handle_mbti_batch_3(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 3)

async def handle_mbti_batch_4(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 4)

async def handle_mbti_batch_5(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 5)

async def handle_mbti_batch_6(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 6)

async def handle_mbti_batch_7(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 7)

async def handle_mbti_batch_8(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch(_get_envelope_data(envelope), 8)


async def handle_mbti_batch_1_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 1)

async def handle_mbti_batch_2_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 2)

async def handle_mbti_batch_3_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 3)

async def handle_mbti_batch_4_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 4)

async def handle_mbti_batch_5_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 5)

async def handle_mbti_batch_6_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 6)

async def handle_mbti_batch_7_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 7)

async def handle_mbti_batch_8_answer(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return await _handle_batch_answer(_get_envelope_data(envelope), 8)
