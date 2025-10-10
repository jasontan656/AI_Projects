<template>
  <!-- 添加按钮 - 圆形+号按钮 -->
  <button
    class="add-button"
    @click="handleClick"
    :disabled="disabled"
    :title="label"
    :aria-label="label"
  >
    <!-- 加号图标 - 使用 Lucide SVG 图标 -->
    <Plus class="add-icon" />
  </button>
</template>

<script setup lang="ts">
// 组件名称声明 - 多词命名规范
defineOptions({
  name: 'AddButton'
})

// Vue 3 组合式 API 导入
import { defineProps, defineEmits, withDefaults } from 'vue'
// Lucide 图标导入
import { Plus } from 'lucide-vue-next'

// Props 接口定义 - 定义组件接受的属性类型
interface Props {
  label?: string // 按钮文字标签
  disabled?: boolean // 禁用状态标识
}

// Props 声明 - 使用 withDefaults 设置默认值
const props = withDefaults(defineProps<Props>(), {
  label: 'Add', // if label 未传入 then 默认显示 "Add"
  disabled: false, // if disabled 未传入 then 默认启用按钮
})

// 事件发射器声明 - 定义组件向外发送的事件
const emit = defineEmits<{
  click: [] // click 事件 - 无参数传递
}>()

// 点击处理函数 - 处理按钮点击逻辑
const handleClick = (): void => {
  // if 按钮未禁用 then 发射点击事件
  if (!props.disabled) {
    emit('click')
  }
  // else 不执行任何操作 - 阻止事件发射
}
</script>

<style scoped>
/* 添加按钮样式 - 圆形+号按钮设计 */
.add-button {
  background: rgb(244, 240, 240); /* 透明背景 */
  color: black; /* 黑色文字 */
  border: none; /* 黑色边框 */
  border-radius: 50%; /* 圆形按钮 */
  width: 32px; /* 按钮宽度 */
  height: 32px; /* 按钮高度 */
  font-size: 20px; /* +号字体大小 */
  cursor: pointer; /* 鼠标悬停指针 */
  display: flex; /* 弹性布局 */
  align-items: center; /* 垂直居中 */
  justify-content: center; /* 水平居中 */
  transition: background 0.2s ease; /* 背景色平滑过渡 */
}

/* 按钮悬停状态 */
.add-button:hover {
  background: rgba(0, 86, 179, 0.1); /* 悬停时淡蓝色背景 */
}

/* 按钮激活状态 */
.add-button:active {
  background: #0056b3; /* 激活时蓝色背景 */
  color: white; /* 激活时白色文字 */
}

/* 禁用状态 */
.add-button:disabled {
  opacity: 0.5; /* 半透明显示禁用状态 */
  cursor: not-allowed; /* 禁用指针 */
}

.add-button:disabled:hover {
  background: transparent; /* 禁用时不显示悬停效果 */
}

/* 图标样式调整 - 优化SVG图标显示 */
.add-icon {
  width: 16px; /* 图标宽度 */
  height: 16px; /* 图标高度 */
  stroke-width: 2; /* 线条粗细 */
}
</style>
