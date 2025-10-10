# 通过 env 调用 python3 解释器执行当前脚本文件
#!/usr/bin/env python3
# 通过 coding 声明设置文件编码为 utf-8 以支持中文字符处理
# -*- coding: utf-8 -*-
"""
step2.py - MBTI result processor (flow-driven version)
Process results, calculate type, output analysis, implements flow context per hub/flow_example.py
"""

import json
import os
import sys
from typing import Dict, List, TypedDict, Union, Optional, Any
# 通过 import 导入 step3 模块，用于在step2完成后触发step3进一步测试
from . import step3

# 添加上级目录到Python路径，以便导入shared_utilities和hub模块
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# 从shared_utilities模块导入Time类，用于生成带时间戳的request ID
# 使用绝对导入路径shared_utilities.time.Time确保跨环境兼容性
from shared_utilities.time import Time
from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from shared_utilities.response import create_error_response, create_success_response

from pymongo.errors import PyMongoError

# 移除直接导入hub子模块，遵循正确的架构分离原则
# Hub将自动处理状态保存，应用模块只负责业务逻辑


# ======== Strong request/response models (Pydantic) ========
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username


class Step2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., description="timestamp_uuidv4 request id")
    user_id: str
    auth_username: str = Field(default="", description="Auth username accompanying the user id")
    flow_id: str = Field(default="mbti_personality_test")
    responses: Dict[int, int] = Field(..., description="{question_index:int score(1-5)}")

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("responses", mode="before")
    def _normalize_responses(cls, v: Any) -> Dict[int, int]:
        data = v or {}
        if not isinstance(data, dict):
            raise ValueError("responses must be a dict")
        normalized: Dict[int, int] = {}
        for k, val in data.items():
            try:
                key_int = int(k)
            except (TypeError, ValueError):
                raise ValueError("responses keys must be int indices") from None
            try:
                score_int = int(val)
            except (TypeError, ValueError):
                raise ValueError("responses values must be integers 1-5") from None
            if score_int < 1 or score_int > 5:
                raise ValueError("score must be between 1 and 5")
            normalized[key_int] = score_int
        return normalized

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)


def _aggregate_responses_from_history(user_id: str, flow_id: str) -> Dict[int, int]:
    responses: Dict[int, int] = {}
    for batch in range(1, 9):
        docs = DatabaseOperations().find(
            "user_chathistory",
            {"user_id": user_id, "flow_id": flow_id, "batch": batch, "event_type": "mbti_answer"},
            {"question_id": 1, "answer": 1, "_id": 0},
        )
        for d in docs or []:
            qid = d.get("question_id", "")
            m = re.match(r"^q_(\d+)_(\d+)$", qid)
            if not m:
                continue
            b = int(m.group(1)); idx = int(m.group(2))
            global_idx0 = (b - 1) * 12 + (idx - 1)
            try:
                score = int(str(d.get("answer", "0")))
            except (TypeError, ValueError):
                continue
            if score < 1 or score > 5:
                continue
            responses[global_idx0] = score
    if len(responses) != 96:
        raise ValueError("MBTI assessment incomplete: need 96 answers")
    return responses


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


# 通过 class 定义 Question 类型字典，包含单个题目结构的精确类型字段
class Question(TypedDict):
    # text 字段定义为 str 类型，用于存储题目文本内容，必须填写
    text: str
    # dimension 字段定义为 str 类型，用于存储题目所属维度，只能是E/S/T/J之一
    dimension: str
    # reverse 字段定义为 bool 类型，用于标识是否为反向题，True表示是反向题
    reverse: bool


# 通过 class 定义 QuestionData 类型字典，包含题目数据文件的完整结构
class QuestionData(TypedDict):
    # mbti_questions 字段定义为 List[Question] 类型，存储包含多个Question对象的题目列表
    mbti_questions: List[Question]


# 通过 class 定义 DimensionDetail 类型字典，包含维度详情的完整结构
class DimensionDetail(TypedDict):
    # score 字段定义为 int 类型，用于存储该维度的原始得分数值
    score: int
    # percentage 字段定义为 int 类型，用于存储该维度的百分比数值
    percentage: int
    # direction 字段定义为 str 类型，用于存储该维度的判定方向字母
    direction: str
    # preference 字段定义为 str 类型，用于存储该维度的偏好方向字母
    preference: str
    # opposite 字段定义为 str 类型，用于存储该维度的对立方向字母
    opposite: str


# 通过 class 定义 MBTIResult 类型字典，包含MBTI评分结果的完整结构
class MBTIResult(TypedDict):
    # raw_scores 字段定义为 Dict[str, int] 类型，用于存储各维度的原始得分数值
    raw_scores: Dict[str, int]
    # percentages 字段定义为 Dict[str, int] 类型，用于存储各维度的百分比数值
    percentages: Dict[str, int]
    # mbti_type 字段定义为 str 类型，用于存储最终计算出的MBTI类型字符串
    mbti_type: str
    # dimension_details 字段定义为 Dict[str, DimensionDetail] 类型，用于存储各维度的详细信息字典
    dimension_details: Dict[str, DimensionDetail]


# 通过 class 定义 TypeCalculationResult 类型字典，包含类型计算的中间结果结构
class TypeCalculationResult(TypedDict):
    # percentages 字段定义为 Dict[str, int] 类型，用于存储各维度的百分比数值字典
    percentages: Dict[str, int]
    # mbti_type 字段定义为 str 类型，用于存储拼接成的MBTI类型字符串
    mbti_type: str
    # dimension_details 字段定义为 Dict[str, DimensionDetail] 类型，用于存储各维度的详情字典
    dimension_details: Dict[str, DimensionDetail]


# 通过 class 定义 MBTIScorer 类，封装所有MBTI评分相关功能的完整实现
class MBTIScorer:
    """MBTI scoring engine"""  # 类功能简述，说明这是一个MBTI测试的评分工具

    # DIMENSION_MAPPING 通过字典创建常量，存储四个维度的字母映射关系，用于后续类型判定
    DIMENSION_MAPPING = {
        # 'E' 键映射到 ['I', 'E'] 列表，E维度低分取索引0的I(内向)，高分取索引1的E(外向)
        'E': ['I', 'E'],
        # 'S' 键映射到 ['N', 'S'] 列表，S维度低分取索引0的N(直觉)，高分取索引1的S(感觉)
        'S': ['N', 'S'],
        # 'T' 键映射到 ['F', 'T'] 列表，T维度低分取索引0的F(情感)，高分取索引1的T(思考)
        'T': ['F', 'T'],
        # 'J' 键映射到 ['P', 'J'] 列表，J维度低分取索引0的P(感知)，高分取索引1的J(判断)
        'J': ['P', 'J']
    }

    # __init__ 方法在创建 MBTIScorer 实例时自动调用，无需传入参数
    def __init__(self):
        # 通过 self._load_questions() 调用私有方法加载题目数据，赋值给 self.questions_data 实例变量存储
        self.questions_data = self._load_questions()

    # _load_questions 方法定义为私有方法，通过 -> QuestionData 返回精确的题目数据类型
    def _load_questions(self) -> QuestionData:
        """Load question data"""  # 方法功能说明，读取JSON格式的题目数据
        # try 块开始尝试执行文件读取操作，捕获可能的异常
        try:
            # 获取当前脚本文件所在目录，然后构建完整的文件路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, 'step1_mbti_questions.json')
            # 通过 with open() 以只读模式打开文件，指定 utf-8 编码，赋值给变量 f
            with open(file_path, 'r', encoding='utf-8') as f:
                # 通过 json.load() 传入文件对象 f 解析JSON数据，返回字典对象赋值给 data 变量
                data = json.load(f)
                # 通过 QuestionData(**data) 将字典 data 解包传入构造函数，转换为精确的QuestionData类型后返回
                return QuestionData(**data)
        # except 捕获 FileNotFoundError 异常，当文件不存在时执行
        except FileNotFoundError:
            # 通过 raise 抛出新的 FileNotFoundError 异常，传入自定义错误信息字符串
            raise FileNotFoundError("step1_mbti_questions.json not found")

    # calculate_scores 方法接收 responses 参数（Dict[str, int]类型），通过 -> MBTIResult 返回完整的评分结果
    def calculate_scores(self, responses: Dict[str, int]) -> MBTIResult:
        """
        计算MBTI得分  # 方法功能：根据用户答案计算各维度得分
        Args:  # 参数说明部分
            responses: {question_index: score} 格式的答案字典  # 说明输入格式
        Returns:  # 返回值说明部分
            包含原始得分、百分比和类型的完整结果  # 说明输出包含哪些内容
        """
        # dimension_scores 通过字典初始化，创建E/S/T/J四个维度的得分计数器，每个维度初始值设为0
        dimension_scores = {'E': 0, 'S': 0, 'T': 0, 'J': 0}

        # 通过 enumerate() 遍历 self.questions_data['mbti_questions'] 列表，获取题目索引idx和题目内容question
        for idx, question in enumerate(self.questions_data['mbti_questions']):
            # 通过 responses[idx] 获取用户对第idx题的原始得分（1-5分，所有题目必答），赋值给 raw_score 变量
            raw_score = responses[idx]
            # 通过 question['dimension'] 获取这道题所属的维度（E/S/T/J之一），赋值给 dimension 变量
            dimension = question['dimension']
            # 通过 question['reverse'] 检查这道题是否为反向题，布尔值赋值给 is_reverse 变量
            is_reverse = question['reverse']

            # processed_score 通过条件表达式计算：如果是反向题则用6减去raw_score，否则直接使用raw_score
            processed_score = 6 - raw_score if is_reverse else raw_score

            # 通过 dimension_scores[dimension] 索引对应维度，将 processed_score 累加到该维度的总分上
            dimension_scores[dimension] += processed_score

        # 通过 self._calculate_mbti_type() 调用私有方法，传入 dimension_scores 参数，计算百分比和类型，结果赋值给 result 变量
        result = self._calculate_mbti_type(dimension_scores)

        # 通过 return 返回包含完整计算结果的字典，包含raw_scores、percentages、mbti_type和dimension_details四个键值对
        return {
            # 'raw_scores' 键赋值为 dimension_scores 字典，存储各维度的原始得分数值
            'raw_scores': dimension_scores,
            # 'percentages' 键赋值为 result['percentages']，存储各维度的百分比数值
            'percentages': result['percentages'],
            # 'mbti_type' 键赋值为 result['mbti_type']，存储最终计算出的MBTI类型字符串
            'mbti_type': result['mbti_type'],
            # 'dimension_details' 键赋值为 result['dimension_details']，存储各维度的详细信息字典
            'dimension_details': result['dimension_details']
        }

    # _calculate_mbti_type 方法接收 scores 参数（Dict[str, int]类型），通过 -> TypeCalculationResult 返回类型计算结果
    def _calculate_mbti_type(self, scores: Dict[str, int]) -> TypeCalculationResult:
        """Calculate MBTI type using Z-Score thresholds"""  # 方法功能：将各维度得分转换为最终MBTI类型
        # percentages 通过字典初始化，用于存储各维度的百分比数值
        percentages = {}
        # mbti_letters 通过列表初始化，用于存储四个维度的判定字母，准备后续拼接成MBTI类型
        mbti_letters = []
        # dimension_details 通过字典初始化，用于存储各维度的详细信息字典
        dimension_details = {}

        # 基于24题（1-5分）的理论分布计算阈值
        # 理论平均分：24题 × 3分 = 72分
        # 理论标准差：约6.6分（通过统计模拟计算）
        THEORETICAL_MEAN = 72.0
        THEORETICAL_STD = 6.6
        HIGH_THRESHOLD = THEORETICAL_MEAN + 0.5 * THEORETICAL_STD  # +0.5 SD ≈ 75.3
        LOW_THRESHOLD = THEORETICAL_MEAN - 0.5 * THEORETICAL_STD   # -0.5 SD ≈ 68.7

        # 通过 scores.items() 遍历四个维度的得分，获取维度名称dimension和对应得分score
        for dimension, score in scores.items():
            # percentage 通过 round() 函数计算：score除以120(总分)乘以100，得到百分比并四舍五入取整
            percentage = round(score / 120 * 100)

            # 使用Z-Score阈值判断偏好方向
            if score > HIGH_THRESHOLD:
                # 高于+0.5 SD，明显偏好该维度
                direction_idx = 1
                preference_strength = "Strong preference"
            elif score < LOW_THRESHOLD:
                # 低于-0.5 SD，明显偏好对立维度
                direction_idx = 0
                preference_strength = "Strong opposite preference"
            else:
                # 在-0.5 SD ~ +0.5 SD之间，中间型/边缘型
                # 取更接近的方向作为主要偏好
                direction_idx = 1 if score >= THEORETICAL_MEAN else 0
                preference_strength = "Balanced/Borderline"

            # mbti_letter 通过 self.DIMENSION_MAPPING[dimension][direction_idx] 从映射表获取对应字母，赋值给变量
            mbti_letter = self.DIMENSION_MAPPING[dimension][direction_idx]

            # percentages[dimension] 索引对应维度位置，将 percentage 值存储到百分比字典中
            percentages[dimension] = percentage
            # 通过 mbti_letters.append() 将 mbti_letter 添加到字母列表末尾
            mbti_letters.append(mbti_letter)

            # dimension_details[dimension] 索引对应维度位置，创建包含详细信息的字典
            dimension_details[dimension] = {
                # 'score' 键赋值为 score 变量，存储该维度的原始得分数值
                'score': score,
                # 'percentage' 键赋值为 percentage 变量，存储该维度的百分比数值
                'percentage': percentage,
                # 'direction' 键赋值为 mbti_letter 变量，存储该维度的最终判定方向字母
                'direction': mbti_letter,
                # 'preference' 键赋值为 self.DIMENSION_MAPPING[dimension][direction_idx]，存储偏好方向字母
                'preference': self.DIMENSION_MAPPING[dimension][direction_idx],
                # 'opposite' 键赋值为 self.DIMENSION_MAPPING[dimension][1 - direction_idx]，存储对立方向字母
                'opposite': self.DIMENSION_MAPPING[dimension][1 - direction_idx],
                # 'preference_strength' 键赋值为 preference_strength，存储偏好强度描述
                'preference_strength': preference_strength,
                # 'z_score' 键计算并存储Z-Score值，表示相对于平均水平的标准差倍数
                'z_score': round((score - THEORETICAL_MEAN) / THEORETICAL_STD, 2)
            }

        # 通过 return 返回包含完整类型计算结果的字典
        return {
            # 'percentages' 键赋值为 percentages 字典，存储各维度的百分比数值
            'percentages': percentages,
            # 'mbti_type' 键通过 ''.join(mbti_letters) 将字母列表拼接成字符串，存储最终MBTI类型
            'mbti_type': ''.join(mbti_letters),
            # 'dimension_details' 键赋值为 dimension_details 字典，存储各维度的详细信息
            'dimension_details': dimension_details
        }



# load_output_templates 函数定义为独立函数，无需传入参数，通过 -> Dict[str, str] 返回模板字典
def load_output_templates() -> Dict[str, str]:
    """Load MBTI output templates"""  # 方法功能：读取输出模板JSON文件
    # try 块开始尝试执行文件读取操作，捕获可能的异常
    try:
        # 获取当前脚本文件所在目录，然后构建完整的文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'step2_mbti_output_templates.json')
        # 通过 with open() 以只读模式打开文件，指定 utf-8 编码，赋值给变量 f
        with open(file_path, 'r', encoding='utf-8') as f:
            # 通过 json.load() 传入文件对象 f 解析JSON数据，返回字典对象后直接返回
            return json.load(f)
    # except 捕获 FileNotFoundError 异常，当文件不存在时执行
    except FileNotFoundError:
        # 通过 raise 抛出新的 FileNotFoundError 异常，传入自定义错误信息字符串
        raise FileNotFoundError("step2_mbti_output_templates.json not found")


# process 函数定义为异步函数，接收 request 参数（Dict[str, Union[str, int, bool, None]]类型），通过 -> Dict[str, Union[str, bool, int]] 返回处理结果字典
def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}


async def process(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Process MBTI step 2 with envelope-compliant fail-fast semantics."""
    request_data = _get_envelope_data(envelope)
    try:
        step_request = Step2Request(**request_data)
    except ValidationError as exc:
        return create_error_response(
            "Invalid payload for mbti_step2",
            error_type="INVALID_INPUT",
            details={"errors": exc.errors()},
        )

    try:
        responses = step_request.responses or {}
        if not responses:
            responses = _aggregate_responses_from_history(step_request.user_id, step_request.flow_id)
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    scorer = MBTIScorer()
    try:
        mbti_result = scorer.calculate_scores(responses)
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    try:
        templates = load_output_templates()
    except FileNotFoundError as exc:
        return create_error_response(
            "MBTI output templates not available",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )
    mbti_type = mbti_result.get("mbti_type")
    if not mbti_type:
        return create_error_response(
            "MBTI type calculation returned empty result",
            error_type="INTERNAL_ERROR",
        )
    analysis_text = templates.get(mbti_type, "Analysis template not found")

    try:
        await _call_mongodb_connector(request_data, mbti_result)
    except PyMongoError as exc:
        return create_error_response(
            "Failed to store MBTI assessment result",
            error_type="DEPENDENCY_ERROR",
            details={"reason": str(exc)},
        )

    step3_request = {
        "request_id": step_request.request_id,
        "user_id": step_request.user_id,
        "auth_username": request_data.get("auth_username", ""),
        "flow_id": step_request.flow_id,
        "next_step": "mbti_step3",
        "mbti_type": mbti_type,
        "previous_step": "mbti_step2",
    }
    step3_result = await step3.process(step3_request)
    if not isinstance(step3_result, dict):
        return create_error_response(
            "mbti_step3 returned unexpected payload",
            error_type="DEPENDENCY_ERROR",
        )
    if not step3_result.get("success", False):
        return create_error_response(
            step3_result.get("error") or "Failed to dispatch mbti_step3 follow-up",
            error_type=step3_result.get("error_type") or "DEPENDENCY_ERROR",
            details={"step3_result": step3_result},
        )

    response_payload = {
        "request_id": step_request.request_id,
        "user_id": step_request.user_id,
        "flow_id": step_request.flow_id,
        "step": "mbti_step2",
        "mbti_type": mbti_type,
        "raw_scores": mbti_result.get("raw_scores", {}),
        "percentages": mbti_result.get("percentages", {}),
        "dimension_details": mbti_result.get("dimension_details", {}),
        "analysis": analysis_text,
        "step2_handshake": True,
        "message": "MBTI assessment completed successfully. Ready for progressive display.",
        "needs_progressive_display": True,
        "wait_for_frontend_confirmation": True,
        "next_step": "mbti_confirm_frontend_state",
    }
    return create_success_response(data=response_payload)



# _call_mongodb_connector 函数定义为异步私有函数，接收 request 和 mbti_result 参数，通过 -> None 不返回任何值
async def _call_mongodb_connector(request: Dict[str, Union[str, int, bool, None]], mbti_result: MBTIResult) -> None:
    """Persist MBTI results to user_profiles with strict fail-fast semantics."""
    from shared_utilities.mango_db.mongodb_connector import DatabaseOperations

    db_ops = DatabaseOperations()
    user_id = request.get("user_id")
    payload = {
        "$setOnInsert": {"user_id": user_id},
        "$set": {
            "mbti.assessment.type": mbti_result["mbti_type"],
            "mbti.assessment.raw_scores": mbti_result.get("raw_scores", {}),
            "mbti.assessment.percentages": mbti_result.get("percentages", {}),
            "mbti.assessment.dimension_details": mbti_result.get("dimension_details", {}),
            "mbti.assessment.completed_at": Time.timestamp(),
            "mbti.assessment.request_id": request.get("request_id"),
            "mbti.assessment.flow_id": request.get("flow_id", "mbti_personality_test")
        }
    }
    db_ops.update("user_profiles", {"user_id": user_id}, payload)

# ======== Module-local step specification (self-contained) ========
MBTI_STEP2_STEP_SPECS = {
    "steps": [
        {
            "step_id": "mbti_step2",
            "handler": "cry_backend.tool_modules.mbti.step2.process",
        }
    ]
}
# MBTI_STEP2_STEP_SPECS(steps=[{step_id/handler}])
# 提供本步骤的自包含路由规范，供模块内 router 聚合
