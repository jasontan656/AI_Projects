workflow:
  name: GitBackup
  description: 全量 push/pull 的 Git 备份工作流；强制 main 分支；基于索引理解项目结构；提交消息由 AI 在“对比当前代码库与远端记录”后自动生成
  language: zh-CN

args:
  MODE:
    required: true
    enum: ["push", "pull"]
    description: 必传；操作模式
  COMMIT_MESSAGE:
    required: false
    description: 可选；自定义提交信息，若缺省则由 AI 自动生成
args_source: arguments
arguments_examples:
  - "MODE=push"
  - "MODE=pull COMMIT_MESSAGE='chore: 同步'"

params:
  MODE: "${ARGS.MODE}"  # 由 args 解析绑定；缺失或非法取值（非 push/pull）则失败
  BRANCH: "main"  # 强制使用 main 分支，禁止创建/切换到其他分支
  REMOTE: "origin"  # 远端名
  REMOTE_URL: "git@github.com:jasontan656/AI_Projects.git"  # 默认远端地址
  COMMIT_MESSAGE: ""  # 可选；为空则自动生成（含时间戳与变更摘要）

io:
  kobe_root_index: "Kobe/index.yaml"
  root_gitignore: ".gitignore"
  kobe_gitignore: "Kobe/.gitignore"

assumptions:
  - 已安装并可调用 git；仓库位于 D:/AI_Projects
  - 远端 REMOTE 已配置可访问

policy:
  - 只允许在 BRANCH=main 分支上操作；禁止创建/切换分支
  - MODE=push 时使用强覆盖策略：推送后以远端为最终状态（--force）
  - MODE=pull 时使用强恢复策略：以远端覆盖本地（reset --hard origin/main）
  - 一切变更遵从 .gitignore 与 Kobe/.gitignore；忽略项不纳入版本控制

steps:
  - id: parse_args
    name: 解析与校验参数
    actions:
      - 解析 $ARGUMENTS 为键值对
      - 校验必传 MODE 是否存在且取值 ∈ {push, pull}
      - 将 MODE 绑定到 params.MODE；将 COMMIT_MESSAGE（若提供）绑定到 params.COMMIT_MESSAGE
    output: [parsed_args]
    gate: 缺失必传参数或取值非法则立即失败

  - id: check_docs
    name: 索引与忽略规则加载
    actions:
      - 读取 io.kobe_root_index
      - 自根遍历：加载 sub_indexes 与 relations.depends_on（仅限 Kobe/ 内部路径）
      - 构建 index_map（path → module.summary/responsibilities/relations）
      - 读取 root_gitignore 与 kobe_gitignore，生成 ignore_patterns
    output: [index_map, ignore_patterns]
    purpose: 在备份前理解项目结构并锁定忽略范围

  - id: ensure_repo
    name: 仓库与分支校验
    actions:
      - 校验当前目录为 git 仓库（git rev-parse --is-inside-work-tree）
      - 校验当前分支为 BRANCH=main；否则立即失败
      - 校验 REMOTE 存在（git remote get-url ${REMOTE}）
      - 若 REMOTE 不存在：git remote add ${REMOTE} ${REMOTE_URL}
      - 若 REMOTE URL 与 params.REMOTE_URL 不一致：git remote set-url ${REMOTE} ${REMOTE_URL}
    output: [current_branch, remote_url]
    gate: 分支非 master 或缺少远端时失败

  - id: analyze_changes
    name: 变更扫描与归档
    actions:
      - 确定基准引用 base_ref = "${REMOTE}/${BRANCH}"
      - 获取变更文件（相对 base_ref 与本地 HEAD）：git diff --name-status ${REMOTE}/${BRANCH}..HEAD
      - 统计变更类型计数（A/M/D/R 等），生成 change_stats
      - 将变更文件映射到模块：依据 index_map 的 path 前缀匹配得到 changed_modules
    output: [changed_files, change_stats, changed_modules]
    purpose: 为 AI 生成提交消息提供结构化输入

  - id: generate_message
    name: 生成 AI 提交信息
    actions:
      - 基于 index_map、changed_files、change_stats、changed_modules 自动生成 commit_message（AI）
      - 提交信息结构：
        - header: "chore(repo): 同步变更 <YYYY-MM-DD HH:mm>"
        - summary: "文件变更 <total> 项（A:<a>/M:<m>/D:<d>/R:<r>）"
        - modules: [模块路径与摘要（来自 index_map.module.summary）]
        - details: 按模块分组列出变更文件列表
        - rationale: "依据索引理解项目结构与关系，生成面向人的简洁摘要"
    output: [commit_message]
    acceptance:
      - commit_message 非空

  - id: mode_push
    name: 全量推送覆盖远端
    when: params.MODE == "push"
    actions:
      - 拉取远端引用（git fetch ${REMOTE} ${BRANCH}）
      - 按忽略规则添加修改（git add -A）
      - 若有待提交更改：
        - 使用提交信息：若 params.COMMIT_MESSAGE 非空则使用之，否则使用 generate_message.commit_message
        - git commit -m "${commit_message}"
      - 强制推送覆盖远端（git push ${REMOTE} ${BRANCH} --force）
    output: [commit_message, local_sha, remote_sha_after]
    acceptance:
      - 远端 ${REMOTE}/${BRANCH} 的最新提交与本地 HEAD 一致

  - id: mode_pull
    name: 全量拉取覆盖本地
    when: params.MODE == "pull"
    actions:
      - 拉取远端引用（git fetch ${REMOTE} ${BRANCH}）
      - 强制重置本地到远端（git reset --hard ${REMOTE}/${BRANCH}）
    output: [local_sha_after]
    acceptance:
      - 本地 HEAD 与 ${REMOTE}/${BRANCH} 的最新提交一致

summary:
  rules:
    - 始终在 master 分支；不创建/切换分支
    - push 使用 --force 覆盖远端；pull 使用 reset --hard 覆盖本地
    - 严格遵守 .gitignore；不将忽略项纳入版本控制