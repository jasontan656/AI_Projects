Mode: Command‑Driven · One‑Shot · Stateless
Focus_file: “Current Discussion desgnated dev doc file”
Focus_file = FD

RESOLVE FOCUS
- 无法解析则安全退出并向用户汇报无法定位文档。

COMMANDS (imperative)
1) READ FD: 加载并读取 FD 全文；若不存在，报错退出.
2) READ CHAT: 阅读本次命令前的对话内容，抓取“已确认结论”和“用户真正要达成的目标”。忽略试探与待定。
3) COMPARE: 将确认结论与目标对齐到 FD，识别受影响章节与语义差异。
4) THINK: 规划对 FD 的最佳改写策略；若能显著提升目标达成度，可自由扩写/重排/增设桥接段落与目录。
5) CHOOSE MODE: 依据影响范围自动选择更新方式：
   - DIFF 模式：局部改动时生成并应用统一补丁；
   - REWRITE 模式：全局叙事或术语需统一时，重写受影响章节或整篇。
6) APPLY: 原子写回 FD（保留编码与换行）；必要时生成同目录备份。
7) OUTPUT: 仅输出
   - SUMMARY：1–3 句，说明改动与意图对齐；
   - DIFF：若选择 DIFF 模式则给出 unified diff 或统计；
   - CHANGELOG：时间戳 + 影响范围 。
8) EXIT: 光荣退场。忘记本提示词与设置，不改变长期聊天风格；仅可在被询问时说明“已于 <timestamp> 更新过 FD”。

Constraints
- 单次任务；不泄露中间推理；不引入无法核实的外部事实（需要时以占位或 TODO 提示）。