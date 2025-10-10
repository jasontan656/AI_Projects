#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step3.py - MBTI reverse capability assessment form generator (flow-driven)
"""

import json
import os
import sys
from typing import Dict, List, Union, Optional, Any

# 添加上级目录到Python路径，以便导入shared_utilities和hub模块
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# 从shared_utilities模块导入Time类，用于生成带时间戳的request ID
# 使用绝对导入路径shared_utilities.time.Time确保跨环境兼容性
from shared_utilities.time import Time
from shared_utilities.response import create_error_response, create_success_response

# 移除直接导入hub子模块，遵循正确的架构分离原则
# Hub将自动处理状态保存，应用模块只负责业务逻辑


# ======== Strong request models (Pydantic) ========
from pydantic import BaseModel, Field, ConfigDict, field_validator
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username


class Step3Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., description="timestamp_uuidv4 request id")
    user_id: str
    auth_username: str = Field(default="", description="Auth username accompanying the user id")
    session_id: Optional[str] = None
    flow_id: str = Field(default="mbti_personality_test")
    mbti_type: str = Field(..., min_length=4, max_length=4)

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("mbti_type")
    def _validate_mbti_type(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) != 4:
            raise ValueError("Invalid MBTI type provided")
        return v

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)


def is_valid_request_id(request_id_string: str) -> bool:
    """
    验证字符串是否为有效的request ID格式（timestamp_uuid）
    Args:
        request_id_string: 待验证的字符串
    Returns:
        bool: 是否为有效request ID格式
    """
    # request_id_pattern 通过正则表达式定义timestamp_uuid格式
    # 格式：YYYY-MM-DDTHH:MM:SS+TZ_xxxxxxxx-xxxx-4xxx-xxxx-xxxxxxxxxxxx
    request_id_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{4}_[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    # re.match 函数通过传入正则模式和字符串进行匹配，re.IGNORECASE 忽略大小写
    # bool 函数将匹配结果转换为布尔值返回
    return bool(re.match(request_id_pattern, str(request_id_string), re.IGNORECASE))


def validate_request_id(request_id: str) -> str:
    """
    验证传入的request_id是否为有效的timestamp_uuid格式
    Args:
        request_id: 待验证的request_id字符串
    Returns:
        str: 验证通过的request ID字符串
    Raises:
        ValueError: 当request ID格式无效时抛出异常
    """
    # if 条件判断检查 request_id 是否为空值或空字符串
    if not request_id:
        # raise 语句抛出 ValueError 异常，传入错误信息字符串
        raise ValueError("Request ID is required and cannot be empty")

    # if 条件判断检查 request_id 是否为有效的timestamp_uuid格式
    if not is_valid_request_id(request_id):
        # raise 语句抛出 ValueError 异常，传入包含无效request ID的错误信息字符串
        raise ValueError(f"Invalid request ID format: {request_id}. Request rejected for security reasons.")

    # return 语句返回验证通过的request ID字符串
    return request_id


# 通过 class 定义 MbtiReverseQuestion 类型字典，包含单个反向问题结构的精确类型字段
class MbtiReverseQuestion:
    """Reverse question data structure"""
    def __init__(self, question_id: int, text: str, options: Dict[str, str]):
        # question_id 字段定义为 int 类型，用于存储问题的唯一标识符
        self.question_id = question_id
        # text 字段定义为 str 类型，用于存储问题文本内容
        self.text = text
        # options 字段定义为 Dict[str, str] 类型，用于存储选项键值对
        self.options = options


def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}


async def process(envelope: Dict[str, Union[str, int, bool, None]]) -> Dict[str, Union[str, bool, int, List, Dict]]:
    """Build reverse capability questionnaire for mbti_step3."""
    request = _get_envelope_data(envelope)
    try:
        req = Step3Request(**request)
    except ValidationError as exc:
        return create_error_response(
            "Invalid payload for mbti_step3",
            error_type="INVALID_INPUT",
            details={"errors": exc.errors()},
        )

    try:
        questions_data = _load_reverse_questions()
        reverse_dimensions = _get_reverse_dimensions(req.mbti_type)
        selected_questions = _extract_questions(questions_data, reverse_dimensions)
        form_schema = _generate_form_schema(selected_questions)
    except FileNotFoundError as exc:
        return create_error_response(
            "Reverse question templates not found",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )
    except json.JSONDecodeError as exc:
        return create_error_response(
            "Reverse question templates invalid",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )
    except KeyError as exc:
        return create_error_response(
            f"Unsupported MBTI dimension: {exc}",
            error_type="INVALID_INPUT",
        )
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    response_payload: Dict[str, Any] = {
        "request_id": req.request_id,
        "user_id": req.user_id,
        "flow_id": req.flow_id,
        "step": "mbti_step3",
        "mbti_type": req.mbti_type,
        "reverse_dimensions": reverse_dimensions,
        "form_data": {"form_schema": form_schema},
        "questions_count": len(selected_questions),
        "next_step": "mbti_step4",
    }
    return create_success_response(
        data=response_payload,
        message="Reverse capability form generated.",
    )
def _load_reverse_questions() -> Dict:
    """Load reverse questions data file"""
    # try 块开始尝试执行文件读取操作，捕获可能的异常
    try:
        # os.path.dirname 函数通过传入 os.path.abspath(__file__) 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # os.path.join 函数通过传入目录路径和文件名拼接完整文件路径
        file_path = os.path.join(current_dir, 'step3_mbti_reversed_questions.json')
        # with open() 语句以只读模式打开文件，指定 utf-8 编码，赋值给变量 f
        with open(file_path, 'r', encoding='utf-8') as f:
            # json.load 函数通过传入文件对象 f 解析JSON数据，返回字典对象
            return json.load(f)
    # except 捕获 FileNotFoundError 异常，当文件不存在时执行
    except FileNotFoundError:
        # raise 语句抛出新的 FileNotFoundError 异常，传入自定义错误信息字符串
        raise FileNotFoundError("step3_mbti_reversed_questions.json not found")


def _get_reverse_dimensions(mbti_type: str) -> List[str]:
    """
    根据MBTI类型计算反向维度
    Args:
        mbti_type: 4位MBTI类型字符串，如"INTJ"
    Returns:
        包含4个反向维度的列表，如["E", "S", "F", "P"]
    """
    # DIMENSION_REVERSE_MAP 通过字典创建常量，存储MBTI维度的反向映射关系
    DIMENSION_REVERSE_MAP = {
        'I': 'E',  # 内向(I) 的反向是 外向(E)
        'E': 'I',  # 外向(E) 的反向是 内向(I)
        'N': 'S',  # 直觉(N) 的反向是 感觉(S)
        'S': 'N',  # 感觉(S) 的反向是 直觉(N)
        'F': 'T',  # 情感(F) 的反向是 思考(T)
        'T': 'F',  # 思考(T) 的反向是 情感(F)
        'P': 'J',  # 感知(P) 的反向是 判断(J)
        'J': 'P'   # 判断(J) 的反向是 感知(P)
    }
    
    # reverse_dimensions 通过列表推导式创建反向维度列表
    # for char in mbti_type 遍历MBTI类型的每个字符
    # DIMENSION_REVERSE_MAP[char] 通过字符索引获取对应的反向维度字符
    reverse_dimensions = [DIMENSION_REVERSE_MAP[char] for char in mbti_type]
    
    # return 语句返回包含4个反向维度字符的列表
    return reverse_dimensions


def _extract_questions(questions_data: Dict, reverse_dimensions: List[str]) -> List[MbtiReverseQuestion]:
    """
    从问题库中提取指定维度的问题
    Args:
        questions_data: 完整的问题数据字典
        reverse_dimensions: 需要提取的反向维度列表
    Returns:
        包含选中问题的MbtiReverseQuestion对象列表
    """
    # selected_questions 通过列表初始化，用于存储提取出的问题对象
    selected_questions = []
    
    # for dimension in reverse_dimensions 遍历需要提取的每个反向维度
    for dimension in reverse_dimensions:
        # questions_data.get 方法通过传入 "dimensionAssessments" 键获取维度评估数据
        # 返回包含所有维度评估的列表，赋值给 dimension_assessments 变量
        dimension_assessments = questions_data.get("dimensionAssessments", [])
        
        # for assessment in dimension_assessments 遍历每个维度评估数据
        for assessment in dimension_assessments:
            # assessment.get 方法通过传入 "assessedAbility" 键获取被评估的能力维度
            assessed_ability = assessment.get("assessedAbility")
            
            # if 条件判断检查被评估能力是否包含当前需要的反向维度
            if assessed_ability and f"{dimension} (" in assessed_ability:
                # assessment.get 方法通过传入 "questions" 键获取该维度的问题列表
                questions = assessment.get("questions", [])
                
                # for question in questions 遍历该维度的每个问题
                for question in questions:
                    # MbtiReverseQuestion 构造函数通过传入问题数据创建问题对象
                    # question.get 方法分别获取问题ID、文本和选项数据
                    # 创建的对象添加到 selected_questions 列表中
                    selected_questions.append(MbtiReverseQuestion(
                        question_id=question.get("reverse_questions_id"),
                        text=question.get("reverse_questions_text"),
                        options=question.get("reverse_questions_options", {})
                    ))
                # break 语句跳出当前循环，找到匹配维度后不再继续查找
                break
    
    # return 语句返回包含所有选中问题对象的列表
    return selected_questions


def _generate_form_schema(questions: List[MbtiReverseQuestion]) -> Dict:
    """
    生成前端表单渲染所需的JSON schema
    Args:
        questions: MbtiReverseQuestion对象列表
    Returns:
        包含完整表单配置的字典
    """
    # form_fields 通过列表初始化，用于存储所有表单字段配置
    form_fields = []
    
    # for i, question in enumerate(questions) 遍历问题列表，获取索引和问题对象
    for i, question in enumerate(questions):
        # field_config 通过字典创建单个字段的配置结构
        field_config = {
            # "field_id" 键通过 f"question_{i}" 格式化字符串生成字段唯一标识符
            "field_id": f"question_{i}",
            # "question_id" 键赋值为 question.question_id，存储问题的原始ID
            "question_id": question.question_id,
            # "field_type" 键设为 "radio"，指定字段类型为单选框
            "field_type": "radio",
            # "label" 键赋值为 question.text，存储问题文本作为字段标签
            "label": question.text,
            # "required" 键设为 True，指定该字段为必填项
            "required": True,
            # "options" 键通过列表推导式转换问题选项格式
            # for key, value in question.options.items() 遍历选项键值对
            # 生成包含 "value" 和 "label" 的字典结构
            "options": [
                {"value": key, "label": value} 
                for key, value in question.options.items()
            ],
            # "validation" 键包含字段验证规则配置
            "validation": {
                "required": True,
                "message": "Please select an answer"
            }
        }
        # form_fields.append 方法将字段配置添加到表单字段列表中
        form_fields.append(field_config)
    
    # schema 通过字典创建完整的表单schema结构
    schema = {
        # "form_title" 键设置表单标题文本
        "form_title": "MBTI Reverse Capability Assessment",
        # "form_description" 键设置表单描述文本
        "form_description": "Please select the answer that best matches your actual situation. All questions must be answered.",
        # "fields" 键赋值为 form_fields 列表，包含所有字段配置
        "fields": form_fields,
        # "submit_config" 键包含提交按钮和处理配置
        "submit_config": {
            "button_text": "Submit Assessment",
            "next_step": "mbti_step4",
            "validation_message": "Please ensure all questions are answered",
            # 明确定义前端提交时需要的字段
            "submit_schema": {
                "step_id": "mbti_step4",
                "required_fields": ["mbti_type", "responses"],
                "field_sources": {
                    "mbti_type": "form_meta.mbti_type",  # 从表单元数据获取
                    "responses": "form_responses"        # 从用户填写的表单响应获取
                }
            }
        },
        # "draft_save" 键包含草稿保存配置
        "draft_save": {
            "enabled": True,
            "storage_key": "mbti_step3_draft",
            "auto_save_interval": 30
        }
    }
    
    # return 语句返回完整的表单schema字典
    return schema


# ======== Module-local step specification (self-contained) ========
MBTI_STEP3_STEP_SPECS = {
    "steps": [
        {
            "step_id": "mbti_step3",
            "handler": "cry_backend.tool_modules.mbti.step3.process",
        }
    ]
}
# MBTI_STEP3_STEP_SPECS(steps=[{step_id/handler}])
# 提供本步骤的自包含路由规范，供模块内 router 聚合





