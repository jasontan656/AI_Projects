/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // DefineComponent 通过泛型参数定义Vue组件类型
  // Props设置为Record<string, unknown>允许任意属性，Data和Setup返回值设置为unknown
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}
