<template>
  <div class="page-container" :class="{ 'dark-mode': isDark }">
    <!-- 顶部导航 -->
    <header class="app-header">
      <div class="header-left">
        <div class="logo">
          <el-icon :size="28" color="#409EFF"><Monitor /></el-icon>
          <span class="app-title">Docker Port Hub</span>
        </div>
      </div>
      <div class="header-right">
        <el-tooltip content="切换暗色模式" placement="bottom">
          <el-button
            :icon="isDark ? 'Sunny' : 'Moon'"
            circle
            @click="toggleDark"
          />
        </el-tooltip>
        <el-tooltip content="刷新数据" placement="bottom">
          <el-button
            icon="Refresh"
            circle
            :loading="loading"
            @click="refreshData"
          />
        </el-tooltip>
      </div>
    </header>

    <!-- 统计信息 -->
    <div class="stats-bar">
      <el-row :gutter="16">
        <el-col :xs="12" :sm="6">
          <div class="stat-card running">
            <div class="stat-icon">
              <el-icon :size="24"><CircleCheckFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.running }}</div>
              <div class="stat-label">运行中</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="stat-card empty">
            <div class="stat-icon">
              <el-icon :size="24" color="#909399"><CircleCloseFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.empty }}</div>
              <div class="stat-label">空闲</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="stat-card total">
            <div class="stat-icon">
              <el-icon :size="24" color="#409EFF"><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total }}</div>
              <div class="stat-label">总端口</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="stat-card scan">
            <div class="stat-icon">
              <el-icon :size="24" color="#E6A23C"><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ scanInterval }}s</div>
              <div class="stat-label">扫描周期</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 搜索和筛选栏 -->
    <div class="filter-bar">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="10" :md="12">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索端口 / 应用名称 / Docker容器..."
            clearable
            @input="onSearchInput"
            @clear="onSearchClear"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :xs="12" :sm="7" :md="6">
          <el-select
            v-model="categoryFilter"
            placeholder="全部分类"
            clearable
            style="width: 100%"
            @change="onFilterChange"
          >
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat || '未分类'"
              :value="cat"
            />
          </el-select>
        </el-col>
        <el-col :xs="12" :sm="7" :md="6">
          <el-select
            v-model="statusFilter"
            placeholder="全部状态"
            clearable
            style="width: 100%"
            @change="onFilterChange"
          >
            <el-option label="运行中" value="RUNNING" />
            <el-option label="空闲" value="EMPTY" />
          </el-select>
        </el-col>
      </el-row>
    </div>

    <!-- 收藏夹 -->
    <div v-if="favorites.length > 0" class="favorites-section">
      <div class="section-title">
        <el-icon><StarFilled /></el-icon>
        <span>收藏的服务</span>
      </div>
      <div class="port-grid">
        <PortCard
          v-for="item in favorites"
          :key="item.port"
          :port-info="item"
          :favorited="true"
          @toggle-favorite="toggleFavorite"
        />
      </div>
      <el-divider />
    </div>

    <!-- 端口卡片列表 -->
    <div class="port-list">
      <div v-if="loading && filteredPorts.length === 0" class="loading-state">
        <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
        <p>正在扫描端口...</p>
      </div>

      <div v-else-if="filteredPorts.length === 0" class="empty-state">
        <el-icon :size="48" color="#909399"><FolderDelete /></el-icon>
        <p>没有匹配的端口</p>
      </div>

      <div v-else class="port-grid">
        <PortCard
          v-for="item in filteredPorts"
          :key="item.port"
          :port-info="item"
          :favorited="favorites.includes(item.port)"
          @toggle-favorite="toggleFavorite"
        />
      </div>
    </div>

    <!-- 底部信息 -->
    <footer class="app-footer">
      <span>Docker Port Hub v1.0</span>
      <span class="dot">·</span>
      <span>内网开发服务导航</span>
      <span class="dot">·</span>
      <span>访问地址: {{ accessPrefix }}</span>
    </footer>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getPorts, searchPorts, getConfig, getStats } from '../api/index.js'
import PortCard from '../components/PortCard.vue'

export default {
  name: 'Dashboard',
  components: { PortCard },
  setup() {
    // 状态
    const ports = ref([])
    const filteredPorts = ref([])
    const loading = ref(true)
    const isDark = ref(false)
    const searchKeyword = ref('')
    const categoryFilter = ref('')
    const statusFilter = ref('')
    const categories = ref([])
    const accessPrefix = ref('')
    const scanInterval = ref(30)
    const stats = ref({ total: 0, running: 0, empty: 0 })
    const favorites = ref([])
    const refreshInterval = ref(null)

    // 加载收藏列表
    function loadFavorites() {
      try {
        const saved = localStorage.getItem('dph_favorites')
        favorites.value = saved ? JSON.parse(saved) : []
      } catch {
        favorites.value = []
      }
    }

    function saveFavorites() {
      localStorage.setItem('dph_favorites', JSON.stringify(favorites.value))
    }

    function toggleFavorite(port) {
      const idx = favorites.value.indexOf(port)
      if (idx >= 0) {
        favorites.value.splice(idx, 1)
      } else {
        favorites.value.push(port)
      }
      saveFavorites()
    }

    // 加载数据
    async function loadData() {
      try {
        const data = await getPorts()
        ports.value = data
        applyFilters()
      } catch (e) {
        console.error('加载端口数据失败:', e)
      } finally {
        loading.value = false
      }
    }

    async function loadConfig() {
      try {
        const cfg = await getConfig()
        categories.value = cfg.categories || []
        accessPrefix.value = cfg.accessPrefix || ''
        scanInterval.value = cfg.scanInterval || 30
      } catch (e) {
        console.error('加载配置失败:', e)
      }
    }

    async function loadStats() {
      try {
        const s = await getStats()
        stats.value = s
      } catch (e) {
        console.error('加载统计失败:', e)
      }
    }

    // 搜索过滤
    function applyFilters() {
      let result = [...ports.value]

      // 关键词搜索
      if (searchKeyword.value) {
        const kw = searchKeyword.value.toLowerCase()
        result = result.filter(item =>
          String(item.port).includes(kw) ||
          item.name.toLowerCase().includes(kw) ||
          item.docker.toLowerCase().includes(kw)
        )
      }

      // 分类筛选
      if (categoryFilter.value) {
        result = result.filter(item => item.category === categoryFilter.value)
      }

      // 状态筛选
      if (statusFilter.value) {
        result = result.filter(item => item.status === statusFilter.value)
      }

      // 排序: 已占用优先, 端口升序
      result.sort((a, b) => {
        if (a.status === 'RUNNING' && b.status === 'EMPTY') return -1
        if (a.status === 'EMPTY' && b.status === 'RUNNING') return 1
        return a.port - b.port
      })

      filteredPorts.value = result
    }

    function onSearchInput() {
      applyFilters()
    }

    function onSearchClear() {
      applyFilters()
    }

    function onFilterChange() {
      applyFilters()
    }

    // 刷新
    async function refreshData() {
      loading.value = true
      await Promise.all([loadData(), loadStats()])
      loading.value = false
    }

    // 暗色模式
    function toggleDark() {
      isDark.value = !isDark.value
      document.documentElement.classList.toggle('dark', isDark.value)
      localStorage.setItem('dph_dark', isDark.value ? '1' : '0')
    }

    onMounted(() => {
      // 加载暗色模式偏好
      const savedDark = localStorage.getItem('dph_dark')
      if (savedDark === '1') {
        isDark.value = true
        document.documentElement.classList.add('dark')
      }

      loadFavorites()
      loadConfig()

      // 首次加载
      Promise.all([loadData(), loadStats()])

      // 自动刷新（30秒）
      refreshInterval.value = setInterval(() => {
        loadData()
        loadStats()
      }, 30000)
    })

    onUnmounted(() => {
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value)
      }
    })

    return {
      ports,
      filteredPorts,
      loading,
      isDark,
      searchKeyword,
      categoryFilter,
      statusFilter,
      categories,
      accessPrefix,
      scanInterval,
      stats,
      favorites,
      toggleFavorite,
      onSearchInput,
      onSearchClear,
      onFilterChange,
      refreshData,
      toggleDark
    }
  }
}
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 0 20px 40px;
  transition: background 0.3s;
}

/* 暗色模式 */
.page-container.dark-mode {
  background: #1a1a2e;
  color: #e0e0e0;
}

.dark-mode .stat-card {
  background: #16213e !important;
  border-color: #0f3460 !important;
}

.dark-mode .filter-bar {
  background: #16213e !important;
}

.dark-mode .app-footer {
  color: #909399;
}

/* 顶部 */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  position: sticky;
  top: 0;
  z-index: 100;
  background: #f0f2f5;
}

.dark-mode .app-header {
  background: #1a1a2e;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-title {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #409EFF, #36d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  gap: 8px;
}

/* 统计 */
.stats-bar {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  margin-right: 14px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.stat-card.running .stat-value { color: #67c23a; }
.stat-card.empty .stat-value { color: #909399; }
.stat-card.total .stat-value { color: #409EFF; }
.stat-card.scan .stat-value { color: #E6A23C; }

/* 筛选栏 */
.filter-bar {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
}

/* 收藏 */
.favorites-section {
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #E6A23C;
  margin-bottom: 12px;
}

/* 端口网格 */
.port-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 80px 0;
  color: #909399;
}

.loading-icon {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  margin-top: 12px;
  font-size: 14px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: #909399;
}

.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}

/* 底部 */
.app-footer {
  text-align: center;
  padding: 24px 0 12px;
  font-size: 13px;
  color: #909399;
}

.dot {
  margin: 0 8px;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-container {
    padding: 0 10px 30px;
  }
  .app-title {
    font-size: 18px;
  }
  .stat-card {
    padding: 12px 16px;
  }
  .stat-value {
    font-size: 20px;
  }
  .port-grid {
    grid-template-columns: 1fr;
  }
}
</style>