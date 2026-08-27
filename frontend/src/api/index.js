import axios from 'axios'

// 创建 axios 实例
const http = axios.create({
  baseURL: '',
  timeout: 10000
})

// 获取所有端口状态
export function getPorts() {
  return http.get('/api/ports').then(res => res.data)
}

// 搜索端口
export function searchPorts(params = {}) {
  return http.get('/api/ports/search', { params }).then(res => res.data)
}

// 获取配置
export function getConfig() {
  return http.get('/api/config').then(res => res.data)
}

// 获取统计
export function getStats() {
  return http.get('/api/stats').then(res => res.data)
}

export default http