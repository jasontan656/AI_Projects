<template>
  <!-- 发送消息按钮 - 使用 Element Plus 按钮组件 -->
  <el-button
    type="primary"
    :disabled="disabled"
    :loading="loading"
    @click="handleClick"
    class="send-message-button"
    :title="label"
    :aria-label="label"
  >
    <!-- 纸飞机图标 - 仅在非加载状态时显示 -->
    <el-icon v-if="!loading">
      <Send />
    </el-icon>
  </el-button>
</template>

<script setup lang="ts">
// 组件名称声明 - 多词命名规范
defineOptions({
  name: 'SendMessageButton'
})

// Vue 3 组合式 API 导入
import { defineProps, defineEmits, withDefaults } from 'vue'
// Element Plus 组件导入
import { ElButton, ElIcon } from 'element-plus'
// Lucide 图标导入
import { Send } from 'lucide-vue-next'

// Props 接口定义 - 定义组件接受的属性类型
interface Props {
  label?: string // 按钮文字标签
  disabled?: boolean // 禁用状态标识
  loading?: boolean // 加载状态标识
}

// Props 声明 - 使用 withDefaults 设置默认值
const props = withDefaults(defineProps<Props>(), {
  label: 'Send', // if label 未传入 then 默认显示 "Send"
  disabled: false, // if disabled 未传入 then 默认启用按钮
  loading: false, // if loading 未传入 then 默认非加载状态
})

// 事件发射器声明 - 定义组件向外发送的事件
const emit = defineEmits<{
  click: [] // click 事件 - 无参数传递
}>()

// 点击处理函数 - 处理按钮点击逻辑
const handleClick = (): void => {
  // if 按钮未禁用 and 未在加载中 then 发射点击事件
  if (!props.disabled && !props.loading) {
    emit('click')
  }
  // else 不执行任何操作 - 阻止事件发射
}
</script>

<style scoped>
/* 发送消息按钮样式 - 透明圆形按钮设计 */
.send-message-button {
  width: 32px; /* 按钮宽度 = 32px */
  height: 32px; /* 按钮高度 = 32px */
  border-radius: 50%; /* 圆形边框 = 50% 圆角 */
  padding: 0; /* 内边距清零 = 紧凑布局 */
  display: flex; /* 弹性盒子 = 居中对齐 */
  align-items: center; /* 垂直居中 = center 对齐 */
  justify-content: center; /* 水平居中 = center 对齐 */
  min-width: unset; /* 最小宽度重置 = 取消默认限制 */
  background: transparent !important; /* 背景透明 = 无背景色 */
  border: 1px solid black; /* 边框移除 = 纯图标显示 */
  color: #606266; /* 图标颜色 = 深灰色 */
}

/* 按钮悬停状态 - 轻微背景色提示交互 */
.send-message-button:hover {
  background: rgba(0, 0, 0, 0.05) !important; /* 悬停背景 = 半透明黑色 */
  color: #409eff; /* 悬停图标颜色 = Element Plus 主题色 */
}

/* 按钮激活状态 */
.send-message-button:active {
  background: rgba(0, 0, 0, 0.1) !important; /* 激活背景 = 稍深半透明 */
}

/* 图标样式调整 - 优化纯图标按钮显示 */
.send-message-button .el-icon {
  margin: 0 !important; /* 图标边距清零 = 完全居中 */
  font-size: 16px; /* 图标大小 = 16px 清晰显示 */
}
</style>
