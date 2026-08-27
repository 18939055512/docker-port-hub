<template>
  <Dashboard />
</template>

<script>
import Dashboard from './views/Dashboard.vue'

export default {
  name: 'App',
  components: { Dashboard }
}
</script>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  background: #f0f2f5;
}

/* 暗色模式 */
html.dark {
  color-scheme: dark;
}

html.dark body {
  background: #1a1a2e;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #909399;
}

/* Element Plus 暗色适配 */
html.dark .el-select__wrapper,
html.dark .el-input__wrapper {
  background-color: #16213e !important;
  box-shadow: 0 0 0 1px #0f3460 inset !important;
}

html.dark .el-select__placeholder,
html.dark .el-input__inner {
  color: #e0e0e0 !important;
}
</style>