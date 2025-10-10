# Enhanced AI Response Generator Prompt

用户输入可以由代理直接提供，或作为命令参数传入——在继续执行提示词之前（若不为空），你**必须**予以考虑。

用户输入：

$ARGUMENTS

### 必需参数
- **USER_PROMPT**: `{USER_PROMPT}` - 用户原始提示词，将被插入到指定位置进行处理



## 核心契约 (Core Contract)


  - id: update_indexes
    name: 索引更新与补全（基于本次开发结果）
    actions:
      - 读取 io.dev_constitution 并定位 index_spec（写作规范与校验规则）
      - 从 Kobe/index.yaml 作为起点加载旧索引并执行如下：
        - 扫描 Kobe/ 下新增的目录（本次变更产生）且缺少 index.yaml 的 new_dirs
        - 对照 index_spec.field_schema 补齐/修正 meta/module/relations/files/notes
        - 更新 relations.depends_on 与 provides_apis（若任务实现引入/暴露了新关系）
        - 更新 files.key_files 与 test_locations（若新增/改动）
        - 为 new_dirs 依据 index_spec.field_schema 生成最小可用 index.yaml：
        - meta.path = 目录相对 Kobe 的路径；owners/stability 合理赋值
        - module.name/summary/responsibilities 来自任务与变更摘要
        - relations 仅包含 Kobe 内部路径；禁止外部引用
        - files.key_files 从变更文件推导；test_locations 如存在则记录
    output: [old_index_map, updated_targets, new_dirs, write_results]
  
    acceptance:
      - 所有写入路径均位于 Kobe/ 内且与 meta.path 一致
      - 新旧索引键结构符合 index_spec.field_schema，内容仅描述目录内事实
      - 对于 new_dirs 均已生成 index.yaml；对于 updated_targets 均已落盘更新

