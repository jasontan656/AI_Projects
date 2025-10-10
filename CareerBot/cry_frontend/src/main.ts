import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

// Global error handler for better observability
const handleGlobalError = (error: Error, context?: string) => {
  console.error(`GLOBAL_ERROR${context ? `_${context}` : ''}:`, error);
  throw error; // Re-throw to maintain error propagation
};

// Initialize app without secure storage
const initializeApp = async () => {
  console.log('APP_INIT: Starting application without secure storage');
};

const app = createApp(App)

// Global error handler
app.config.errorHandler = (err, instance, info) => {
  console.error('VUE_ERROR_HANDLER:', {
    error: err,
    component: instance?.$options.name || 'Unknown',
    info
  });
  
  // Special handling for recursive update errors
  const errorMessage = err instanceof Error ? err.message : String(err);
  if (errorMessage.includes('Maximum recursive updates exceeded')) {
    handleGlobalError(new Error('Recursive update detected in Vue component'), 'RECURSIVE_UPDATE');
  }
  
  // Removed secure storage error handling
  
  throw err; // Always propagate the error
};

app.use(ElementPlus)
app.use(createPinia())
app.use(router)

// Initialize app and mount
initializeApp().then(() => {
  console.log('APP_MOUNT_START: Mounting Vue application');
  app.mount('#app')
  console.log('APP_MOUNT_SUCCESS: Vue application mounted');
}).catch((error) => {
  console.error('APP_INIT_FAILED:', error);
  // Still mount the app even if initialization fails
  app.mount('#app')
});
