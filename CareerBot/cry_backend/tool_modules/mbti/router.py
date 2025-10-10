from typing import Dict, Any, Callable, List
import asyncio
import inspect

from . import step1
from . import step2
from . import step3
from . import step4
from . import step5
try:
    from . import display_handler
except ImportError:
    display_handler = None


class MBTIRouter:
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
        specs1 = getattr(step1, "MBTI_STEP1_STEP_SPECS", {}) or {}
        self._register_from_specifications(specs1)
        specs2 = getattr(step2, "MBTI_STEP2_STEP_SPECS", {}) or {}
        self._register_from_specifications(specs2)
        specs3 = getattr(step3, "MBTI_STEP3_STEP_SPECS", {}) or {}
        self._register_from_specifications(specs3)
        specs4 = getattr(step4, "MBTI_STEP4_STEP_SPECS", {}) or {}
        self._register_from_specifications(specs4)
        specs5 = getattr(step5, "MBTI_STEP5_STEP_SPECS", {}) or {}
        self._register_from_specifications(specs5)
        if display_handler is not None:
            specs_display = getattr(display_handler, "MBTI_DISPLAY_STEP_SPECS", {}) or {}
            self._register_from_specifications(specs_display)

    def get_langchain_tools(self) -> List[Dict[str, Any]]:
        """Describe MBTI router for LangChain tool cataloguing."""
        return [
            {
                "name": "mbti_router",
                "description": "Routes MBTI envelopes across questionnaire steps and result handlers.",
                "callable": self.route,
            }
        ]

    def route(self, envelope: Dict[str, Any]) -> Any:
        """Nested router: validate envelope and route using payload.route.path."""
        payload: Dict[str, Any] = envelope.get("payload") or {}

        # Strict validation of routing fields
        route = payload.get("route") or {}
        path: List[str] = route.get("path") if isinstance(route, dict) else None
        if not isinstance(path, list) or not path or not all(isinstance(seg, str) and seg for seg in path):
            return {"success": False, "error": "payload.route.path is required", "error_type": "INVALID_INPUT"}

        data_obj = payload.get("data")
        if data_obj is None or not isinstance(data_obj, dict):
            return {"success": False, "error": "payload.data must be an object", "error_type": "INVALID_INPUT"}

        # Map nested path to concrete step_id
        # Convention: ["mbti", "mbti_step1", "mbti_batch", "1"] → "mbti_batch_1"
        step_identifier = self._resolve_step_id_from_path(path)
        if not step_identifier:
            return {"success": False, "error": "Invalid route.path", "error_type": "INVALID_INPUT"}

        handler_callable = self.step_id_to_handler_map.get(step_identifier)
        if not handler_callable:
            return {"success": False, "error": f"Unknown step: {step_identifier}", "error_type": "STEP_NOT_FOUND"}

        # Pass full envelope to handlers for nested validation and context
        result = handler_callable(envelope)
        if inspect.iscoroutine(result):
            # Handler is async - need to run it synchronously in tool context
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            
            if loop is None:
                # No event loop running - create one and run
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(result)
                finally:
                    try:
                        loop.close()
                    except (RuntimeError, ValueError, OSError):
                        pass
            else:
                # Event loop is running - this shouldn't happen in tool context
                # but if it does, we need to handle it
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        lambda: asyncio.run(result)
                    ).result()
        return result

    def _resolve_step_id_from_path(self, path: List[str]) -> str:
        """Translate nested route path to step_id.
        Rules:
          - ["mbti", "mbti_step1"] → "mbti_step1"
          - ["mbti", "mbti_batch", "N"] → "mbti_batch_N" (1..8)
          - ["mbti", "mbti_batch_answer", "N"] → "mbti_batch_N_answer" (1..8)
          - ["mbti", "mbti_stepX"] → "mbti_stepX" (X in 2..5)
        """
        try:
            if len(path) >= 2 and path[0] == "mbti":
                second = path[1]
                if second == "mbti_step1" and len(path) == 2:
                    return "mbti_step1"
                if second == "mbti_batch" and len(path) == 3 and path[2].isdigit():
                    n = int(path[2])
                    if 1 <= n <= 8:
                        return f"mbti_batch_{n}"
                if second == "mbti_batch_answer" and len(path) == 3 and path[2].isdigit():
                    n = int(path[2])
                    if 1 <= n <= 8:
                        return f"mbti_batch_{n}_answer"
                if second in {"mbti_step2", "mbti_step3", "mbti_step4", "mbti_step5"}:
                    return second
        except (ValueError, IndexError, TypeError):
            return ""
        return ""


router = MBTIRouter()


def get_langchain_tools() -> List[Dict[str, Any]]:
    return router.get_langchain_tools()
