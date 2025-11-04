from __future__ import annotations

import concurrent.futures
import os
import random
import traceback
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console

from .config_loader import resolve_path, get_llm_config

BASE_DIR = Path(__file__).resolve().parent
ROOT = resolve_path("workspace_root")
TEMPLATE_PATH = resolve_path("yaml_template")
ENV_PATH = resolve_path("env_file")
TARGET_FIRST_DIR = ROOT / "PreArrangedEmploymentVisa9G"
OUTPUT_EXT = ".yaml"
MODEL = "gpt-5-2025-08-07"
MAX_WORKERS = 10

SYSTEM_PROMPT_FALLBACK = """
system_role: "STRUCTURE_CONVERTER_V2"
description: >
  将业务说明文档（Markdown）转换为标准化 YAML（v2）。
  目的：为客服机器人提供“骨架+占位符”数据结构，便于本地脚本按键名拼接替换。
  绝不补写或推断。仅输出 YAML，无任何解释或注释。

reference_template: |
  version: ""
  updated_at: ""
  default_language: "zh-CN"
  aliases: []
  department: ""
  name: ""
  slug: ""
  type: "reference"
  semantic_profile:
    intent_id: ""
    category: ""
    tags: []
  service_overview: ""
  applicability:
    items: {}
  preconditions:
    required: {}
    not_eligible: {}
  pre_required_documents:
    mandatory: {}
    conditional: {}
  process:
    steps: {}
    variants: {}
    notes: ""
  pricing:
    metadata:
      last_verified: ""
      source: ""
    items: {}
  deliverables:
    description: ""
    items: {}
  kpis:
    processing_time: ""
  risks:
    items: {}
  info_collection:
    applicant: {}
    spouse: {}
    father: {}
    mother: {}
    children: {}
    dependents: {}
    employment: {}
    authorization: {}
    arrival_info: {}
    travel_history: {}
    compliance: {}
    additional_details: {}
  acknowledgement_flags:
    data_privacy_consent: ""
    certification_statement: ""
  faq:
    qas: {}
  disclaimers:
    items: {}
  service_related:
    links: {}

schema_rules:
  - 一级与二级键名必须与 reference_template 完全一致，顺序相同，不得新增/改名/重排。
  - 所有“容器”必须是 map（字典），并以第三级“动态ID”作为键；以下容器禁止使用数组：
    pricing.items, deliverables.items, process.steps, process.variants, risks.items,
    faq.qas, disclaimers.items, applicability.items, preconditions.required,
    preconditions.not_eligible, pre_required_documents.mandatory, service_related.links,
    info_collection.applicant/spouse/father/mother/children/dependents/employment/authorization/arrival_info/travel_history/compliance/additional_details。
  - 唯一允许的数组：
    aliases, semantic_profile.tags,
    pre_required_documents.conditional.{trigger-id}.documents（字符串数组）, 
    process.variants.{variant-id}.extra_requirements（字符串数组）。
  - pre_required_documents.conditional 为 map：
    { trigger-id: { trigger: "…", documents: [] } }。若没有任何条件触发，输出空 map {}。
  - 条目对象字段集合必须固定：
    pricing.items 采用“分组-明细-属性”三段式结构：
      pricing.items.{group-id} = { label, details, total? }
      其中：
        label: 分组的人类可读名称（如 "Top 1000 企业 · 主申请人 · 1年"）。
        details: map，键为 {detail-id}（如 visa-fee, acr-icard, visa-sticker, express-lane, lrf 等），值为 { amount, notes, attr }；
        total: 可选，对应分组汇总金额对象 { amount, notes, attr }（若无法精确汇总则 amount.value 置空）。
    deliverables.items.{id} = { name, usage }；
    process.steps.{id} = { order, title, description }；
    process.variants.{id} = { name, trigger, description, extra_requirements }；
    faq.qas.{id} = { question, answer }。
  - info_collection.* 下每个字段条目必须为“字段对象（field object）”，不可为纯字符串：
    info_collection.(applicant|spouse|father|mother|children|dependents|employment|authorization|arrival_info|travel_history|compliance|additional_details).{field-id}
      = { label, type, required, format, pattern, example, notes }
    说明：
      label: 字段的人类可读名称（中文）；
      type: 取值之一 [string, integer, number, boolean, date, datetime, enum]；
      required: 取值 [true, false]（字符串，非布尔）；
      format: 可选，细分格式（如 passport-no, iso-date, e164-phone, email, country-iso2）；
      pattern: 可选，正则；
      example: 可选，示例值（不含个人真实信息）；
      notes: 可选，补充说明。
  - 金额对象（amount）必须是对象而非字符串，且满足：
      基本字段：
        amount.currency: 三位大写货币（如 PHP、USD、EUR），类型 str；
        amount.display: 原样展示用字符串（如 "PHP 10,630"），类型 str，可为空字符串；
        amount.value: 金额的整数数值，类型 int 或 null；
      变动金额表达（其一）：
        amount.range: { min: int, max: int }；或
        amount.tiers: [ { value: int, condition: str }, ... ]；
      规则：
        - 若源文为“以现场/以OR为准”等不确定表达：value 置 null，display 可为空，具体说明写入 notes。
        - 不能将金额写为自由文本；必须使用 amount 对象承载货币与数值。
      适用范围：details.{detail-id}.amount 与 total.amount 均遵循上述结构。
  - 详情对象（details.{detail-id}）必须包含 attr，用于指明类型：
      attr.amount.currency: "str"；attr.amount.value: "int" 或 "int|null"；
      如存在 range：attr.amount.range.min/max = "int"；
      如存在 tiers：attr.amount.tiers.value = "int"，attr.amount.tiers.condition = "str"；
      attr.notes = "str"；
      禁止出现 optional/variable 等无关键。
  - 缺失信息：字符串键写为 ""；容器键写为 {}；数组键写为 []。禁止省略键。
  - Map 插入顺序需遵循源文出现顺序（用于前端有序渲染）。
  - 禁止输出超出模板的任意键；禁止输出注释/Markdown/解释性文字。

id_rules:
  - 第三级动态ID采用 kebab-case，可复现、可读，由条目“标题/名称/触发语”确定性派生。
  - 先做规范化（去括号/特殊符号→分词→英文或拼音化→连字符），冲突时追加后缀（例如 -v2、-1y、-main）。
  - 不得使用随机串或时间戳。
  - pricing 分组与明细命名：
      group-id：由“企业分层/人员类别/年限”等组合规范化（如 top1000-main-1y、nontop1000-dependent-1y），不包含空格与中文；
      detail-id：使用费用项目的语义化英文短名（如 visa-fee、acr-icard、visa-sticker、express-lane、lrf、clearance）。

atomic_field_policy:
  - 目的：避免将多个语义字段合并为一个键，确保后续数据采集与类型校验。
  - 针对 info_collection.*：任何复合表述（含“/”“与”“及”“和”“&”“、”“and”等连接词或“（号码/有效期）”样式）必须拆分为多个原子字段：
      例如：
        护照信息（号码/有效期）→ passport-number, passport-expiry
        姓名 → last-name, first-name, middle-name（若无中间名，仍保留字段，required 可为 false）
        联系方式（手机/邮箱）→ phone-mobile, email
  - info_collection 字段 ID 禁止包含连接词（and/与/及/&/、/+/\/）；一经出现，视为错误，需拆分为原子字段。
  - 原子字段的 field object.type 必须与语义一致：
      number/integer/boolean/date/datetime 等需准确标注；避免将年龄、人数等标注为 string。

mapping_guide:
  - name/slug/department/type/default_language：按字面/既定默认。
    department 缺省固定填 "BureauOfImmigration"；
    slug 必须给出：优先用英文标题规范化；若无法确定，使用 CONTEXT.service_dir_name 规范化生成。
  - semantic_profile.intent_id/category/tags：依据标题与上下文提炼；无法确定则 intent_id/category 仍需给出合理规范值，tags 可为空数组。
  - service_overview：提炼“服务概览”一段；不存在则 ""。
  - applicability/preconditions/risks：逐条转写为 map 的 {id: "text"}（按出现顺序）。
  - pre_required_documents.mandatory：常规材料转写为 map 的 {doc-id: "text"}；conditional 见 schema。
  - process.steps：将步骤转写为 map；order 按源文（可为字符串 "1"、"2A" 等）。
  - pricing.items：按“企业分层 × 人员类别 × 年限”等维度生成分组（group-id）。
    每个分组内，用 details 列举费用子项；每个子项使用 amount（对象）+ notes + attr（类型说明）。
    可选填 total（对象）；若源文无一致汇总或需以 OR 为准，则 total.amount.value 置 null 并在 notes 说明。
  - deliverables/items、faq/qas：逐条映射为 map。
  - info_collection.*：将字段提示转写为 map 的 {field-id: "text"}，按分组归类。
    （覆盖）改为转写为“字段对象（field object）”：{field-id: { label, type, required, format, pattern, example, notes }}；
    对于复合表述按 atomic_field_policy 拆分为多个 field-id；常见规范化：
      last-name/first-name/middle-name；passport-number/passport-expiry；
      phone-mobile/email；address-line1/address-city/address-province/address-country/address-postal-code。
  - acknowledgement_flags：若源文包含以下任一关键词或语义（不区分大小写），必须生成一句话说明：
      CGAF、Data Privacy、Affidavit of Undertaking、Certification/Declaration、thumbmark/拇指印、签名/签署/宣誓。
    若完全无相关表述，保持为空字符串。

output_rules:
  - 仅输出 YAML。不得输出除 YAML 外的任何字符。

quality_gates:
  - 若任何禁止数组的容器下出现数组或缺失键，视为错误；改为 map 或填空结构再输出。
  - 金额不满足 amount 规则、随意补写内容、或出现未定义键名，视为错误；修正或置空。
  - 若 slug 为空或 department 为空，视为错误；必须按 mapping_guide 规则补齐（允许使用 CONTEXT.service_dir_name）。
"""

try:
  LLM_CONFIG = get_llm_config("convert_yaml")
except KeyError as exc:
  raise RuntimeError("config.yaml 缺少 llm.convert_yaml 配置。") from exc

MODEL = LLM_CONFIG.get("model")
SYSTEM_PROMPT = LLM_CONFIG.get("system_prompt")

if not MODEL or not SYSTEM_PROMPT:
  raise RuntimeError("llm.convert_yaml 需要同时提供 model 与 system_prompt。")

console = Console()


def load_env() -> None:
  if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
  else:
    load_dotenv()


def find_base_doc(directory: Path) -> Path | None:
  preferred = directory / f"{directory.name}.md"
  if preferred.exists():
    return preferred
  for candidate in sorted(directory.glob("*.md")):
    if candidate.name == "PDFSUM.md" or "rewritten" in candidate.stem.lower():
      continue
    return candidate
  return None


def gather_tasks() -> List[Tuple[Path, Path]]:
  directories = sorted(p for p in ROOT.iterdir() if p.is_dir())
  if TARGET_FIRST_DIR.exists():
    directories = [TARGET_FIRST_DIR] + [d for d in directories if d != TARGET_FIRST_DIR]

  tasks: List[Tuple[Path, Path]] = []
  for directory in directories:
    base_doc = find_base_doc(directory)
    if not base_doc:
      console.print(f"[yellow]Skip (no base doc):[/yellow] {directory.relative_to(ROOT)}")
      continue
    output_path = directory / f"{directory.name}{OUTPUT_EXT}"
    tasks.append((base_doc, output_path))
  return tasks


def read_template() -> str:
  if not TEMPLATE_PATH.exists():
    raise FileNotFoundError(f"YAML 模板缺失: {TEMPLATE_PATH}")
  return TEMPLATE_PATH.read_text(encoding="utf-8")


def pick_sample_tasks(tasks: List[Tuple[Path, Path]]) -> Tuple[List[Tuple[Path, Path]], List[Tuple[Path, Path]]]:
  if not tasks:
    return [], []

  remaining = tasks.copy()
  samples: List[Tuple[Path, Path]] = []

  dir_to_task = {task[0].parent: task for task in remaining}
  nine_g_dir = TARGET_FIRST_DIR
  if nine_g_dir in dir_to_task:
    samples.append(dir_to_task[nine_g_dir])
    remaining.remove(dir_to_task[nine_g_dir])

  available = remaining.copy()
  if available:
    extra_count = min(4, len(available))
    extra_tasks = random.sample(available, extra_count)
    samples.extend(extra_tasks)
    for task in extra_tasks:
      remaining.remove(task)

  # If the 9G directory is missing, still sample at least five (or all) from the remaining set
  if not samples and remaining:
    extra_count = min(5, len(remaining))
    samples = random.sample(remaining, extra_count)
    for task in samples:
      remaining.remove(task)

  return samples, remaining


def run_concurrent(tasks: List[Tuple[Path, Path]], template_text: str, stage_label: str) -> bool:
  if not tasks:
    return True

  console.print(f"[cyan]{stage_label}：并发处理 {len(tasks)} 个目录…[/cyan]")
  max_workers = min(MAX_WORKERS, len(tasks))
  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {
      executor.submit(process_single, task, template_text): task
      for task in tasks
    }
    for future in concurrent.futures.as_completed(futures):
      _, output_path = futures[future]
      rel = output_path.relative_to(ROOT)
      try:
        _, ok, error = future.result()
        if ok:
          console.print(f"[green]Written YAML:[/green] {rel}")
        else:
          console.print(f"[red]Failed {rel}: {error}")
          return False
      except Exception as exc:
        console.print(f"[red]Worker exception for {rel}: {exc}")
        return False
  return True


def call_llm(base_doc: str, template_text: str, context: dict) -> str:
  client = OpenAI()
  ctx_lines = [
    f"service_dir_name: {context.get('service_dir_name','')}",
    f"base_doc_filename: {context.get('base_doc_filename','')}",
    f"relative_dir: {context.get('relative_dir','')}",
  ]
  context_block = "\n".join(ctx_lines)

  user_content = [
    {"type": "input_text", "text": "请将以下 Markdown 业务文档转换为符合 schema 的 YAML，严格遵守系统指令。"},
    {"type": "input_text", "text": f"### CONTEXT\n{context_block}"},
    {"type": "input_text", "text": f"### BASE_DOC\n{base_doc}"},
  ]
  user_content.append({"type": "input_text", "text": f"### YAML_TEMPLATE\n{template_text}"})

  response = client.responses.create(
    model=MODEL,
    input=[
      {"role": "system", "content": SYSTEM_PROMPT},
      {"role": "user", "content": user_content},
    ],
  )
  if hasattr(response, "output_text") and response.output_text:
    return response.output_text.strip()

  data = response.model_dump()
  chunks = []
  for item in data.get("output", []):
    if item.get("type") != "message":
      continue
    for piece in item.get("content", []):
      if piece.get("type") == "output_text" and "text" in piece:
        chunks.append(piece["text"])
  return "\n".join(chunks).strip()


def process_single(task: Tuple[Path, Path], template_text: str) -> Tuple[Path, bool, str]:
  base_path, output_path = task
  try:
    base_text = base_path.read_text(encoding="utf-8", errors="ignore")
    ctx = {
      "service_dir_name": base_path.parent.name,
      "base_doc_filename": base_path.name,
      "relative_dir": str(base_path.parent.relative_to(ROOT)) if str(base_path).startswith(str(ROOT)) else "",
    }
    yaml_text = call_llm(base_text, template_text, ctx)
    output_path.write_text(yaml_text, encoding="utf-8")
    return output_path, True, ""
  except Exception as exc:
    return output_path, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"


def process_files(tasks: List[Tuple[Path, Path]]) -> None:
  load_env()
  template_text = read_template()

  if not tasks:
    console.print("[red]未找到可处理的目录。[/red]")
    return

  sample_tasks, remaining = pick_sample_tasks(tasks)
  if not sample_tasks:
    console.print("[red]未找到可用于抽样验证的目录。[/red]")
    return

  console.print(f"[cyan]抽样验证阶段：共 {len(sample_tasks)} 个目录（包含 9G + 随机4个）。[/cyan]")
  if not run_concurrent(sample_tasks, template_text, "抽样阶段"):
    console.print("[red]抽样阶段出现错误，流程终止。[/red]")
    return

  if not remaining:
    console.print("[bold green]所有目录都在抽样阶段完成，无剩余任务。[/bold green]")
    return

  console.print(f"[yellow]抽样阶段完成。输入 Y 开始并发处理剩余 {len(remaining)} 个目录（最多 {MAX_WORKERS} 个线程）。其他键退出。[/yellow]")
  choice = input().strip().lower()
  if choice not in {"y", "yes"}:
    console.print("[red]已终止剩余任务，请复核输出后再运行。[/red]")
    return

  if not run_concurrent(remaining, template_text, "批量阶段"):
    console.print("[red]批量阶段出现错误。[/red]")
    return

  console.print("[bold green]所有 YAML 已生成，请进一步校验。[/bold green]")


if __name__ == "__main__":
  TASKS = gather_tasks()
  process_files(TASKS)
