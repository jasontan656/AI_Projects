# ======== Auth internal router (module-local) ========
# 发现与路由：从各子模块读取步骤定义与处理器引用，
# 依据 envelope.payload.step_id 分发到正确处理函数。

from __future__ import annotations
from typing import Dict, Any, Callable, List
from pydantic import BaseModel, ValidationError
from shared_utilities.response import create_error_response, create_success_response
import inspect

# 子模块规范来源（各子模块提供 *STEP_SPECS 常量与处理器）
try:
    from . import reset_password
except (ImportError, ValidationError):
    reset_password = None
try:
    from . import email_register
except (ImportError, ValidationError):
    email_register = None
try:
    from . import email_login
except (ImportError, ValidationError):
    email_login = None
try:
    from . import oauth_google
except (ImportError, ValidationError):
    oauth_google = None
try:
    from . import oauth_facebook
except (ImportError, ValidationError):
    oauth_facebook = None
try:
    from . import logout
except (ImportError, ValidationError):
    logout = None


class AuthRouter:
    """模块内路由器：聚合子模块步骤定义并提供分发。"""

    def __init__(self) -> None:
        self.step_id_to_handler_map: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._load_step_specifications()

    def _register_from_specifications(self, specifications: Dict[str, Any]) -> None:
        steps = specifications.get("steps", []) if isinstance(specifications, dict) else []
        for step_definition in steps:
            step_identifier: str = step_definition.get("step_id", "")
            handler_dotted_path: str = step_definition.get("handler", "")
            if not step_identifier or not handler_dotted_path:
                continue
            module_path, function_name = handler_dotted_path.rsplit(".", 1)
            module_obj = __import__(module_path, fromlist=[function_name])
            handler_callable = getattr(module_obj, function_name, None)
            if callable(handler_callable):
                self.step_id_to_handler_map[step_identifier] = handler_callable

    def _load_step_specifications(self) -> None:
        # 从重置密码模块读取规范
        if reset_password is not None:
            reset_specs = getattr(reset_password, "RESET_PASSWORD_STEP_SPECS", {}) or {}
            self._register_from_specifications(reset_specs)

        # 从邮箱注册模块读取规范
        if email_register is not None:
            email_specs = getattr(email_register, "EMAIL_REGISTER_STEP_SPECS", {}) or {}
            self._register_from_specifications(email_specs)

        # 从邮箱登录模块读取规范
        if email_login is not None:
            login_specs = getattr(email_login, "EMAIL_LOGIN_STEP_SPECS", {}) or {}
            self._register_from_specifications(login_specs)

        # 从 Google OAuth 模块读取规范
        if oauth_google is not None:
            google_specs = getattr(oauth_google, "GOOGLE_OAUTH_STEP_SPECS", {}) or {}
            self._register_from_specifications(google_specs)

        # 从 Facebook OAuth 模块读取规范
        if oauth_facebook is not None:
            fb_specs = getattr(oauth_facebook, "FACEBOOK_OAUTH_STEP_SPECS", {}) or {}
            self._register_from_specifications(fb_specs)

        # 从登出模块读取规范
        if logout is not None:
            logout_specs = getattr(logout, "LOGOUT_STEP_SPECS", {}) or {}
            self._register_from_specifications(logout_specs)

    def get_langchain_tools(self) -> List[Dict[str, Any]]:
        """Describe auth router as a LangChain tool for orchestrator registration."""
        return [
            {
                "name": "auth_router",
                "description": "Routes auth envelopes to domain-specific auth handlers.",
                "callable": self.route,
            }
        ]

    def route(self, envelope: Dict[str, Any]) -> Any:
        payload: Dict[str, Any] = envelope.get("payload") or {}
        route = payload.get("route") or {}
        path: List[str] | None = route.get("path") if isinstance(route, dict) else None
        if not isinstance(path, list) or not path or not all(isinstance(seg, str) and seg for seg in path):
            return create_error_response("payload.route.path is required", error_type="INVALID_INPUT")

        step_identifier = self._resolve_step_id(path)
        if not step_identifier:
            return create_error_response("Invalid route.path", error_type="INVALID_INPUT")

        handler_callable = self.step_id_to_handler_map.get(step_identifier)
        if handler_callable is None:
            return create_error_response(f"Unknown step: {step_identifier}", error_type="STEP_NOT_FOUND")

        result = handler_callable(envelope)
        if inspect.iscoroutine(result):
            raise RuntimeError("Auth step handlers must not return coroutines")

        if isinstance(result, BaseModel):
            return create_success_response(data=result.model_dump())
        return result

    def _resolve_step_id(self, path: List[str]) -> str:
        """Map nested path to auth step_id.
        Examples:
          - ["auth", "auth_login"] → auth_login
          - ["auth", "oauth_google_url"] → oauth_google_url
          - ["auth", "oauth_google_callback"] → oauth_google_callback
          - ["auth", "oauth_facebook_url"] → oauth_facebook_url
          - ["auth", "oauth_facebook_callback"] → oauth_facebook_callback
          - ["auth", "auth_logout"] → auth_logout
        """
        try:
            if len(path) >= 2 and path[0] == "auth":
                second = path[1]
                if second in self.step_id_to_handler_map:
                    return second
                for segment in path[1:]:
                    if segment in self.step_id_to_handler_map:
                        return segment
                # Static route aliases for direct tool access (e.g., from auth_tool_handler)
                # These are valid business routes, not legacy code
                allowed = {
                    "auth_login",
                    "oauth_google_url",
                    "oauth_google_callback",
                    "oauth_facebook_url",
                    "oauth_facebook_callback",
                    "auth_logout",
                }
                for segment in path[1:2]:
                    if segment in allowed:
                        return segment
        except (ValueError, IndexError, TypeError):
            return ""
        return ""


router = AuthRouter()


def get_langchain_tools() -> List[Dict[str, Any]]:
    return router.get_langchain_tools()










