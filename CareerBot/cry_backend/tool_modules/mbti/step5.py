#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step5.py - MBTI reverse capability final report generator
"""

# import 语句通过 json 模块名导入用于JSON数据读取和解析操作
import json
# import 语句通过 os 模块名导入用于文件路径处理操作
import os
# import 语句通过 re 模块名导入用于request ID格式验证的正则表达式操作
# import 语句通过 sys 模块名导入用于路径操作
import sys
# from...import 语句通过 typing 模块导入类型提示工具，使用精确类型定义
from typing import Dict, List, Union, Optional, Any

# 添加上级目录到Python路径，以便导入shared_utilities模块
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# 从shared_utilities模块导入Time类，用于生成带时间戳的request ID
# 使用绝对导入路径shared_utilities.time.Time确保跨环境兼容性
from shared_utilities.time import Time

# 导入数据库操作类，用于写入profile和archive
from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from shared_utilities.response import create_error_response, create_success_response
from pymongo.errors import PyMongoError

# 移除直接导入hub子模块，遵循正确的架构分离原则
# Hub将自动处理状态保存，应用模块只负责业务逻辑


# ======== Strong request models (Pydantic) ========
from pydantic import BaseModel, Field, ConfigDict, field_validator
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username
from .errors import MBTIDatabaseError


class Step5Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., description="timestamp_uuidv4 request id")
    user_id: str
    auth_username: str = Field(default="", description="Auth username accompanying the user id")
    flow_id: str = Field(default="mbti_personality_test")
    mbti_type: str = Field(..., min_length=4, max_length=4)
    reverse_dimensions: List[str] = Field(..., min_length=4, max_length=4)
    dimension_scores: Dict[str, int] = Field(...)

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("mbti_type")
    def _validate_mbti_type(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) != 4:
            raise ValueError("Invalid MBTI type provided")
        return v

    @field_validator("reverse_dimensions")
    def _validate_reverse_dims(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list) or len(v) != 4:
            raise ValueError("reverse_dimensions must contain 4 items")
        for ch in v:
            if not isinstance(ch, str) or len(ch) != 1:
                raise ValueError("reverse_dimensions items must be single characters")
        return v

    @field_validator("dimension_scores")
    def _validate_scores(cls, v: Dict[str, int]) -> Dict[str, int]:
        if not isinstance(v, dict) or not v:
            raise ValueError("dimension_scores must be a non-empty dict")
        for k, s in v.items():
            if not isinstance(k, str) or len(k) != 1:
                raise ValueError("dimension_scores keys must be single-character dimensions")
            if not isinstance(s, int) or s < 0:
                raise ValueError("dimension_scores values must be non-negative integers")
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


# 通过 class 定义 MbtiReportGenerator 类，封装最终报告生成功能的完整实现
class MbtiReportGenerator:
    """MBTI reverse capability report generator"""

    # __init__ 方法在创建 MbtiReportGenerator 实例时自动调用，无需传入参数
    def __init__(self):
        # 通过 self._load_output_templates() 调用私有方法加载输出模板，赋值给实例变量
        self.output_templates = self._load_output_templates()

    # _load_output_templates 方法定义为私有方法，通过 -> Dict 返回输出模板字典
    def _load_output_templates(self) -> Dict:
        """Load final output template data"""
        # try 块开始尝试执行文件读取操作，捕获可能的异常
        try:
            # os.path.dirname 函数通过传入 os.path.abspath(__file__) 获取当前脚本所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # os.path.join 函数通过传入目录路径和文件名拼接完整文件路径
            file_path = os.path.join(current_dir, 'step5_final_output_template.json')
            # with open() 语句以只读模式打开文件，指定 utf-8 编码，赋值给变量 f
            with open(file_path, 'r', encoding='utf-8') as f:
                # json.load 函数通过传入文件对象 f 解析JSON数据，返回字典对象
                return json.load(f)
        # except 捕获 FileNotFoundError 异常，当文件不存在时执行
        except FileNotFoundError:
            # raise 语句抛出新的 FileNotFoundError 异常，传入自定义错误信息字符串
            raise FileNotFoundError("step5_final_output_template.json not found")

    # generate_report 方法接收 mbti_type、reverse_dimensions、dimension_scores 参数
    def generate_report(self, mbti_type: str, reverse_dimensions: List[str], dimension_scores: Dict[str, int]) -> Dict[str, Union[str, List]]:
        """
        生成最终反向能力报告
        Args:
            mbti_type: 用户的MBTI类型，如"INTJ"
            reverse_dimensions: 反向维度列表，如["E", "S", "F", "P"]
            dimension_scores: 各维度得分字典，如{"E": 2, "S": 1, "F": 3, "P": 0}
        Returns:
            包含完整报告内容的字典
        """
        # report_sections 通过列表初始化，用于存储各维度的报告段落
        report_sections = []
        # self.output_templates.get 方法通过传入 "outputTemplates" 键获取输出模板字典
        templates = self.output_templates.get("outputTemplates", {})
        
        # for i, reverse_dim in enumerate(reverse_dimensions) 遍历反向维度列表，获取索引和维度字符
        for i, reverse_dim in enumerate(reverse_dimensions):
            # mbti_type[i] 通过索引获取原始MBTI类型的对应位置字符
            original_dim = mbti_type[i]
            # f"{original_dim}_to_{reverse_dim}" 通过格式化字符串生成模板键名
            template_key = f"{original_dim}_to_{reverse_dim}"
            # dimension_scores.get 方法通过传入反向维度获取该维度得分，默认值为0
            score = dimension_scores.get(reverse_dim, 0)
            
            # templates.get 方法通过传入模板键名获取该维度的模板列表，默认值为空列表
            dimension_templates = templates.get(template_key, [])
            # _select_template_by_score 方法通过传入模板列表和得分选择合适模板
            selected_template = self._select_template_by_score(dimension_templates, score)
            
            # if 条件判断检查是否成功选择到模板
            if selected_template:
                # section 通过字典创建单个维度的报告段落结构
                section = {
                    "dimension": f"{original_dim} → {reverse_dim}",  # 维度转换标识
                    "score": score,                                   # 该维度得分
                    "score_range": selected_template.get("scoreRange", ""),  # 得分范围
                    "content": selected_template.get("template", "")         # 报告内容文本
                }
                # report_sections.append 方法将段落字典添加到报告段落列表中
                report_sections.append(section)
        
        # report 通过字典创建完整的报告结构
        report = {
            "title": f"{mbti_type} Reverse Capability Assessment Report",
            "mbti_type": mbti_type,
            "reverse_dimensions": reverse_dimensions,
            "dimension_scores": dimension_scores,
            "report_sections": report_sections,
            "summary": self._generate_summary(mbti_type, dimension_scores)
        }
        
        # return 语句返回包含完整报告内容的字典
        return report

    # _select_template_by_score 方法接收 templates 和 score 参数，返回选中的模板字典
    def _select_template_by_score(self, templates: List[Dict], score: int) -> Optional[Dict]:
        """
        根据得分选择合适的模板
        Args:
            templates: 该维度的模板列表
            score: 维度得分，范围0-3
        Returns:
            匹配的模板字典，如果没有匹配则返回None
        """
        # for template in templates 遍历模板列表中的每个模板字典
        for template in templates:
            # template.get 方法通过传入 "scoreRange" 键获取该模板的得分范围字符串
            score_range = template.get("scoreRange", "")
            
            # if 条件判断检查得分是否在0-1范围内且模板范围包含 "0-1"
            if score <= 1 and "0-1" in score_range:
                # return 语句返回匹配的模板字典
                return template
            # elif 条件判断检查得分是否等于2且模板范围包含 "2 points"
            elif score == 2 and "2 points" in score_range:
                # return 语句返回匹配的模板字典
                return template
            # elif 条件判断检查得分是否等于3且模板范围包含 "3 points"
            elif score == 3 and "3 points" in score_range:
                # return 语句返回匹配的模板字典
                return template
        
        # return 语句返回 None，当没有匹配的模板时
        return None

    # _generate_summary 方法接收 mbti_type 和 dimension_scores 参数，返回总结字符串
    def _generate_summary(self, mbti_type: str, dimension_scores: Dict[str, int]) -> str:
        """
        生成报告总结
        Args:
            mbti_type: 用户的MBTI类型
            dimension_scores: 各维度得分字典
        Returns:
            报告总结文本
        """
        # sum 函数通过传入 dimension_scores.values() 计算所有维度得分总和
        total_score = sum(dimension_scores.values())
        # len 函数通过传入 dimension_scores 计算维度数量
        avg_score = total_score / len(dimension_scores)
        
        # if 条件判断检查平均得分是否小于1.5
        if avg_score < 1.5:
            flexibility_level = "Low"
            summary_text = "You show typical preference patterns in reverse capability. Consider deliberate practice to build balance."
        # elif 条件判断检查平均得分是否小于2.5
        elif avg_score < 2.5:
            flexibility_level = "Medium"
            summary_text = "You have some reverse capability and can use non-preferred skills when needed. Keep developing this balance."
        else:
            flexibility_level = "High"
            summary_text = "You demonstrate strong reverse capability, flexibly using various skills. Avoid excessive switching that may cause fatigue."
        
        # f-string 通过格式化字符串拼接完整的总结文本，包含MBTI类型、灵活性水平和总结内容
        return f"As type {mbti_type}, your reverse capability flexibility is {flexibility_level}. {summary_text}"


def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}


async def process(envelope: Dict[str, Union[str, int, bool, None, Dict, List]]) -> Dict[str, Union[str, bool, int, List, Dict]]:
    """Finalize MBTI assessment results for mbti_step5."""
    request = _get_envelope_data(envelope)
    try:
        req = Step5Request(**request)
    except ValidationError as exc:
        return create_error_response(
            "Invalid payload for mbti_step5",
            error_type="INVALID_INPUT",
            details={"errors": exc.errors()},
        )

    generator = MbtiReportGenerator()
    try:
        final_report = generator.generate_report(req.mbti_type, req.reverse_dimensions, req.dimension_scores)
    except FileNotFoundError as exc:
        return create_error_response(
            "Final report templates not found",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )
    except json.JSONDecodeError as exc:
        return create_error_response(
            "Final report templates invalid",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    try:
        await write_mbti_profile_and_archive(
            req.user_id,
            req.mbti_type,
            final_report,
            req.dimension_scores,
            req.request_id,
        )
    except MBTIDatabaseError as exc:
        return create_error_response(
            "Failed to persist MBTI final results",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )

    response_payload: Dict[str, Any] = {
        "request_id": req.request_id,
        "user_id": req.user_id,
        "flow_id": req.flow_id,
        "step": "mbti_step5",
        "mbti_type": req.mbti_type,
        "dimension_scores": req.dimension_scores,
        "final_report": final_report,
        "completed": True,
    }
    return create_success_response(
        data=response_payload,
        message="MBTI assessment finalized.",
    )
async def write_mbti_profile_and_archive(
    user_id: str,
    mbti_type: str,
    final_report: str,
    dimension_scores: Dict,
    request_id: str,
) -> None:
    """Persist MBTI final report and archive snapshot."""
    db_ops = DatabaseOperations()
    payload = {
        "": {"user_id": user_id},
        "": {
            "mbti.final.type": mbti_type,
            "mbti.final.report": final_report,
            "mbti.final.dimension_scores": dimension_scores,
            "mbti.final.completed_at": Time.timestamp(),
            "mbti.final.request_id": request_id,
            "mbti.final.version": "v1.0",
        },
    }
    try:
        db_ops.update("user_profiles", {"user_id": user_id}, payload)
    except PyMongoError as exc:
        raise MBTIDatabaseError("Failed to write MBTI final report") from exc
# ======== Module-local step specification (self-contained) ========
MBTI_STEP5_STEP_SPECS = {
    "steps": [
        {
            "step_id": "mbti_step5",
            "handler": "cry_backend.tool_modules.mbti.step5.process",
        }
    ]
}
# MBTI_STEP5_STEP_SPECS(steps=[{step_id/handler}])
# 提供本步骤的自包含路由规范，供模块内 router 聚合




