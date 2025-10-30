---

env_policy:
  no_hardcode: true

prompts:
  enforcement: conditional
  include_mode: inline_snapshot
  embed_as: python_literal
  location:
    section: Prompts
    anchor: prompts_snapshot
  variables:
    required: []
    must_resolve: true
    sources_allowed: [env, repo, header]
  redaction:
    no_secrets_in_doc: true
    deny_patterns: [sk-*, api_key=*, token=*]

  triggers:
    section_exists: Prompts
    anchor_exists: prompts_snapshot
    fences_any_of: [yaml, json, text]
    tags_any: [ai, agent, prompt, llm]
    has_agents_spec: true
doc_contract:
  mode: python_narrative_code
  python_version: "3.11+"
  allow_inline_calls: true
  allow_chained_calls: true
  line_kinds: [def, class, import, from, for, while, if, elif, else, try, except, with, return, assign, call, read, write, error, note, source]
  layout:
    narrative_may_be_plaintext: true
    code_line_prefixes: [from, import, class, def, if, elif, else, try, except, for, while, with, return]
  narration_rules:
    import_explained: required
    def_explained: required
    call_expansion: required_1_to_2_lines
    types_cn_alias_required:
      str: 字符串
      int: 整数
      list: 列表
      dict: 字典
      Path: 路径
    function_coverage: all
  ordering:
    prefer_chinese_then_code: true
  templates:
  examples_snippet: |
    """文件: {files.path}
    模块: {files.primary_module}
    同步策略: {files.sync_policy}  ← 文档为真相源；代码生成/同步以此路径为准
    目的: 先中文解释，再给真实 import/def/调用/赋值/类型注解；关键调用后 1–2 行动作语义扩展；生成内容可直译为可运行代码。
    """
    
    """从 python 内置功能 __future__ 导入 annotations：
    用途：推迟类型注解解析，使当前作用域可引用稍后定义的类型名；有利于类型检查与跨模块依赖，不改变运行时行为。"""
    from __future__ import annotations
    
    """从标准库 pathlib 导入 Path（路径）：
    动机：用“路径”替代“字符串”表达文件系统路径，获得跨平台拼接/存在性/规范化等能力；比直接拼接斜杠更稳健。"""
    from pathlib import Path
    
    """从 typing 导入 Protocol（协议）、TypedDict（字典类型）、Iterable（可迭代）、Sequence（序列）：
    意图：用“协议”描述依赖外形（便于注入与替换），用“字典类型”声明返回结构，用“可迭代/序列”约束集合语义。"""
    from typing import Protocol, TypedDict, Iterable, Sequence
    
    """依赖接口外形（protocol）——运行期注入真实实现；此处仅给“能力签名”：
    Filesystem（文件系统读写/遍历/存在性），Tokenizer（文本分词），Ranker（相关性重排），IndexStore（倒排索引存储）。"""
    class Filesystem(Protocol):
        def listdir(self, root: Path) -> Iterable[Path]: ...
        def read_text(self, path: Path, encoding: str = "utf-8") -> str: ...
        def exists(self, path: Path) -> bool: ...
    
    class Tokenizer(Protocol):
        def split(self, text: str, max_tokens: int = 2048) -> list[str]: ...
    
    class Ranker(Protocol):
        def score(self, docs: Sequence[str], top_k: int = 50) -> list[int]: ...
    
    class IndexStore(Protocol):
        def append(self, tokens: list[str]) -> None: ...
        def lookup(self, query: str) -> list[str]: ...
        def size(self) -> int: ...
        def count(self) -> int: ...
    
    """返回结构（字典类型）：
    index_id（字符串）＝由路径推导；size（整数）＝当前倒排条目数。"""
    class IndexStats(TypedDict):
        index_id: str
        size: int
    
    """函数：build_index —— 构建/追加构建倒排索引（def_explained=required）
    整体行为（中文→代码顺序）：
    1) 校验路径存在且可读；不存在/不可读 → 抛 NOT_FOUND / ACCESS_DENIED
       read: fs.exists(collection_path)；error: NOT_FOUND | ACCESS_DENIED；source: repo
    2) 遍历目录 → 逐文档读取 → 分词 → 写入索引
       read: fs.listdir / fs.read_text；call: tokenizer.split(text, max_tokens=2048)
       write: index.append(tokens)（追加 posting，不覆盖既有条目）
       call_expansion: 分词＝按空白/标点切分；过滤停用词；Unicode 规范化；产出词面/位置/频次特征；不修改原文
    3) 返回 {"index_id": 路径推导, "size": index.size()}；指标：index_build_time_ms.p95 < 300_000；source: tests
    类型别名使用（types_cn_alias_required）：str＝字符串；list＝列表；dict＝字典；Path＝路径；int＝整数。"""
    def build_index(fs: Filesystem, tokenizer: Tokenizer, index: IndexStore, collection_path: Path, mode: str) -> IndexStats:
        if not fs.exists(collection_path):
            raise FileNotFoundError("NOT_FOUND: collection_path")  # 提前失败，避免无谓 IO（error）
    
        docs: Iterable[Path] = fs.listdir(collection_path)         # read：目录遍历（可迭代的路径集合）
        for fp in docs:
            text: str = fs.read_text(fp, "utf-8")                 # read：以 UTF-8 读取文件（字符串）
            tokens: list[str] = tokenizer.split(                  # call：真实调用形态，直译可运行
                text=text,
                max_tokens=2048,
            )
            """调用扩展：BM 分词流程：按空白/标点切分；过滤停用词；做 Unicode NFC 规范化；仅生成 tokens，不改原文。"""
            index.append(tokens)                                  # write：将 tokens 形成 posting，追加写入倒排索引
    
        result: IndexStats = {
            "index_id": f"idx::{collection_path.as_posix()}",
            "size": index.size(),                                 # read：索引大小，要求 size ≥ 0
        }
        return result
    
    """函数：query_index —— 查询索引（只读路径）
    行为：
    1) 候选集：read: index.lookup(query) 基于倒排表获取初筛集合（可能未排序）
    2) 重排：call: ranker.score(docs, top_k)＝BM25 统计项 + 语义向量余弦相似度加权融合
    3) 返回：按相关度降序的文档 ID 列表；长度 ≤ top_k；source: repo | tests"""
    def query_index(index: IndexStore, ranker: Ranker, query: str, top_k: int = 50) -> list[str]:
        candidates: list[str] = index.lookup(query)               # read：倒排表检索
        order: list[int] = ranker.score(docs=candidates, top_k=top_k)  # call：相关性重排
        """调用扩展：BM25（基于词项统计）与语义向量（余弦相似度）加权融合；top_k 控制结果窗口。"""
        return [candidates[i] for i in order]                     # return：相关度降序 ID 列表
    
    """示例（examples_min）：Golden ≥1；Counter ≥2；“输入/期望”可直译为测试"""
    def _examples() -> None:
        return None
    
    #@anchor:prompts_snapshot
    PROMPT_CATALOG: dict = {"system": "You are the Index Agent.", "version": "v1"}
    PROMPT_VARS_SCHEMA: dict = {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "properties": {}, "required": []}
    banner: |
    """
    文件: <相对路径>   ← 相对 {REPO_ROOT}（禁止盘符）
    模块: <包名.模块名>
    同步策略: doc_is_source
    目的: 先中文解释，再给真实 import/def/调用/赋值/类型注解；关键调用后 1–2 行动作语义；可直译运行。
    """
  generator:
    order: [banner, imports, types_aliases, deps_protocols, returns_typed_dicts, functions, examples, prompts]

  authoring_manifesto:
    - 文档即代码：产出必须可直译为 Python 源文件；保留真实标识符/调用/括号/赋值/类型注解与缩进。
    - 先中文后代码：先用中文解释“为什么/做什么/副作用/约束”，再给真实 import/def/调用/赋值/返回。
    - 调用要还原语义：每个关键调用后 1–2 行中文解释其隐藏的动作与副作用（call_expansion）。
    - 函数必须解释：每个 def 顶部用中文概述目的、输入/输出与副作用（def_explained）。
    - 显式读/写/错误：出现 IO/网络/存取/异常处，写出 read/write/call/error/source 行。
    - 术语中文化：str=字符串、int=整数、list=列表、dict=字典、Path=路径，贯穿全文。
    - Prompt 属于代码：以 python 常量内联 PROMPT_CATALOG 与 PROMPT_VARS_SCHEMA，并锚定 prompts_snapshot。
    - 单一事实源：files.path 指向的模块与本文一致；以文档为真相源（doc_is_source）。
  authoring_protocol:
    - 使用 templates.banner 生成三引号文件抬头（文件/模块/同步策略/目的）。
    - 对每条 import：先写中文用途与作用域，再写真实 import 语句。
    - 声明依赖协议/返回 TypedDict：给出中文用途与字段语义。
    - 对每个函数：写中文函数解释（目的/输入输出/副作用/指标/来源）→ 写真实 def 与代码体。
    - 对关键调用：紧随 1–2 行中文动作语义扩展（call_expansion），避免“黑箱调用”。
    - 对读/写/错误：就近写 read:/write:/error:/source 行，使副作用与来源可机检。
    - 写 Examples：_examples() 中给 Golden ≥1、Counter ≥2 的“输入/期望”。
    - 写 Prompts：按 templates.prompts_block 以内联 python 常量给出快照与变量 Schema。
  pitfalls:
    - 仅给骨架/占位：不允许（必须是可直译的生产级内容）。
    - 用英文泛词代替中文叙述：不允许（能中文即中文）。
    - 省略副作用：不允许（read/write/call/error/source 缺一不可）。
    - 未解释的 import/def/call：不允许（violations: import_explained/def_explained/call_expansion_present）。
  examples_snippet: |
    """
    文件: {files.path} | 模块: {files.primary_module} | 同步策略: {files.sync_policy}
    目的: 先中文解释，再给真实 import/def/调用/赋值/类型注解；关键调用后 1–2 行动作语义；可直译运行。
    """
    从 pathlib 导入 Path（路径）：跨平台路径处理与存在性检查。
    from pathlib import Path
    
    def build_index(collection_path: Path) -> dict:
        """构建索引：read→call→write→return；指标: index_build_time_ms.p95 < 300_000；source: tests"""
        text = Path(collection_path).read_text(encoding="utf-8")   # read
        tokens = tokenize(text, max_tokens=2048)                    # call
        """调用扩展：按空白/标点切分；过滤停用词；Unicode 规范化；仅生成 tokens，不改原文。"""
        index_append(tokens)                                        # write
        return {"index_id": f"idx::{collection_path}", "size": len(tokens)}  # source: repo
fence:
  languages_allowed: [python]
  no_exec_sandbox: off

ci:
  rules:
    - on: [pre_merge, repo_scan]
      when: prompts.enforcement == "required" OR prompts.triggers_matched == true
      checks: [prompt_snapshot_present, prompt_schema_present, prompt_vars_resolved, prompt_redaction_passed, agent_prompts_complete]
  required_checks: [header_shape_valid, python_ast_parseable, docstring_coverage, narrative_present, side_effects_declared, import_explained, def_explained, call_expansion_present, types_cn_alias_present, banner_present, anchors_present, env_no_hardcode, examples_min, file_banner_declared, no_absolute_drive_letters]
---
