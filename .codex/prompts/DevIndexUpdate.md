meta:
  task: "Kobe 全库 index.yaml 占位创建 与 全量更新（分离流程）"
  date: "2025-10-10"

workflows:
  - name: "占位创建（仅补缺）"
    steps:
      - name: "进入项目根目录"
        do: "切换到 D:\\AI_Projects 作为当前工作目录"

      - name: "扫描 Kobe 目录结构"
        do: "遍历 Kobe/ 下的所有子目录（包含空目录），收集目录清单并包含 Kobe 根目录"

      - name: "为缺失的 index.yaml 生成最小骨架"
        do: |
          对清单中的每个目录：
          - 若不存在 index.yaml，则创建。
          - 写入最小骨架，字段包含：
            - meta.version="1.0"
            - meta.schema_version="1"
            - meta.path=该目录相对于仓库根的正斜杠相对路径
            - meta.last_updated=当天日期（YYYY-MM-DD）
            - meta.owners=["kobe-core"]（如无更具体 owner）
            - meta.stability="alpha"
            - module.name=目录名
            - module.summary="占位目录索引"
            - module.responsibilities=["占位"]
            - module.non_goals=["仅占位，不含实现"]
            - module.entry_points=[]
            - relations.depends_on=[]
            - relations.used_by=[]
            - relations.provides_apis=[]
            - relations.reasons=["目录存在性记录"]
            - files.key_files=[]
            - files.test_locations=[]
            - sub_indexes=[]
            - notes=["自动生成最小骨架"]

      - name: "清理临时产物"
        do: "移除扫描过程中产生的任何临时清单或缓存文件"

  - name: "全量更新（同步至代码现状）"
    steps:
      - name: "进入项目根目录"
        do: "切换到 D:\\AI_Projects 作为当前工作目录"

      - name: "收集所有 index.yaml"
        do: "在 Kobe/** 中查找所有 index.yaml，形成文件清单"

      - name: "更新 index.yaml"
        do: "语义理解并逐个读写将每个 index.yaml 的 内容同步至代码库现状(禁止一次性脚本)"

   