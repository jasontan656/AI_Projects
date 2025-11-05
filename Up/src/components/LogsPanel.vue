<template>
  <section class="logs-panel">
    <header class="logs-panel__header">
      <div>
        <h2>实时日志</h2>
        <p>连接 WebSocket/SSE 后实时查看节点执行记录。</p>
      </div>
      <div class="logs-panel__actions">
        <el-switch v-model="autoScroll" active-text="自动滚动" />
        <el-button size="small" @click="simulateEvent">模拟事件</el-button>
        <el-button size="small" type="primary" @click="toggleConnection">
          {{ connected ? "断开" : "连接" }}
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="!connected"
      title="尚未连接日志流"
      type="info"
      description="点击“连接”启用模拟 SSE，后端上线后将替换为真实接口。"
      show-icon
      class="logs-panel__alert"
    />

    <el-scrollbar class="logs-panel__stream" ref="scrollRef">
      <div
        v-for="log in visibleLogs"
        :key="log.id"
        class="logs-panel__item"
      >
        <span class="logs-panel__timestamp">{{ log.timestamp }}</span>
        <span class="logs-panel__level" :data-level="log.level">{{ log.level }}</span>
        <span class="logs-panel__message">{{ log.message }}</span>
      </div>
      <p v-if="!visibleLogs.length" class="logs-panel__empty">
        暂无日志，等待连接或触发动作。
      </p>
    </el-scrollbar>
  </section>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import { ElMessage } from "element-plus";
import { v4 as uuid } from "uuid";

const connected = ref(false);
const autoScroll = ref(true);
const logs = ref([]);
const scrollRef = ref(null);

const formatTimestamp = () => {
  const now = new Date();
  return now.toLocaleTimeString("zh-CN", { hour12: false }) + "." + now.getMilliseconds();
};

const pushLog = (level, message) => {
  logs.value = [
    ...logs.value,
    { id: uuid(), timestamp: formatTimestamp(), level, message },
  ].slice(-200);

  if (autoScroll.value) {
    nextTick(() => {
      const wrap = scrollRef.value?.wrapRef;
      if (wrap) {
        wrap.scrollTop = wrap.scrollHeight;
      }
    });
  }
};

const toggleConnection = () => {
  connected.value = !connected.value;
  pushLog("INFO", connected.value ? "已建立日志流连接。" : "日志流连接已关闭。");
};

const simulateEvent = () => {
  if (!connected.value) {
    ElMessage.info("请先连接日志流");
    return;
  }
  const sample = [
    ["INFO", "节点 draft_llm 调用模板 tmpl_onboarding"],
    ["WARN", "工具调用延迟超过 1.5s，尝试重试"],
    ["ERROR", "输出节点序列化失败，已回滚到最近一次成功状态"],
  ];
  const pick = sample[Math.floor(Math.random() * sample.length)];
  pushLog(pick[0], pick[1]);
};

const visibleLogs = computed(() => logs.value);
</script>

<style scoped>
.logs-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
  min-height: 420px;
}

.logs-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.logs-panel__header h2 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.logs-panel__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.logs-panel__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.logs-panel__alert {
  margin-bottom: 0;
}

.logs-panel__stream {
  flex: 1;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  padding: var(--space-3);
}

.logs-panel__item {
  display: grid;
  grid-template-columns: 120px 64px 1fr;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  background: #fff;
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
  font-size: var(--font-size-xs);
  box-shadow: var(--shadow-panel);
}

.logs-panel__timestamp {
  color: var(--color-text-tertiary);
}

.logs-panel__level[data-level="INFO"] {
  color: var(--color-success);
}

.logs-panel__level[data-level="WARN"] {
  color: #d97706;
}

.logs-panel__level[data-level="ERROR"] {
  color: #e03131;
}

.logs-panel__empty {
  text-align: center;
  color: var(--color-text-secondary);
  margin: var(--space-3) 0 0;
}
</style>
