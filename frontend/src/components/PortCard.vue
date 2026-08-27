<template>
  <div class="port-card" :class="[cardClass, { favorited }]">
    <!-- 卡片头部 -->
    <div class="card-header">
      <span class="port-number">{{ portInfo.port }}</span>
      <div class="header-actions">
        <el-tooltip content="收藏服务" placement="top">
          <el-button
            size="small"
            text
            :type="favorited ? 'warning' : 'info'"
            :icon="favorited ? 'StarFilled' : 'Star'"
            circle
            @click.stop="$emit('toggle-favorite', portInfo.port)"
          />
        </el-tooltip>
      </div>
    </div>

    <!-- 状态指示灯 -->
    <div class="status-row">
      <span class="status-dot" :class="statusClass"></span>
      <span class="status-text">{{ statusText }}</span>
      <el-tag v-if="portInfo.status === 'RUNNING'" size="small" type="success" effect="light">
        RUNNING
      </el-tag>
      <el-tag v-else size="small" type="info" effect="plain">
        EMPTY
      </el-tag>
      <el-tag
        v-if="portInfo.category"
        size="small"
        type="primary"
        effect="plain"
        class="category-tag"
      >
        {{ portInfo.category }}
      </el-tag>
    </div>

    <!-- 应用名称 -->
    <div class="app-name" :title="portInfo.name">
      {{ portInfo.name || '暂无应用' }}
    </div>

    <!-- 备注 -->
    <div v-if="portInfo.remark" class="app-remark" :title="portInfo.remark">
      {{ portInfo.remark }}
    </div>

    <!-- Docker 信息 -->
    <div v-if="portInfo.status === 'RUNNING'" class="docker-info">
      <div class="docker-line" v-if="portInfo.docker">
        <el-icon :size="14" color="#409EFF"><Folder /></el-icon>
        <span class="label">容器:</span>
        <span class="value">{{ portInfo.docker }}</span>
      </div>
      <div class="docker-line" v-if="portInfo.image">
        <el-icon :size="14" color="#409EFF"><DataBoard /></el-icon>
        <span class="label">镜像:</span>
        <span class="value" :title="portInfo.image">{{ portInfo.image }}</span>
      </div>
    </div>

    <!-- 进程信息 -->
    <div v-if="portInfo.status === 'RUNNING' && (portInfo.process || portInfo.process_dir)" class="docker-info process-info">
      <div class="docker-line" v-if="portInfo.process && portInfo.process !== portInfo.name">
        <el-icon :size="14" color="#67c23a"><Cpu /></el-icon>
        <span class="label">进程:</span>
        <span class="value" :title="portInfo.process_cmd">{{ portInfo.process }}</span>
      </div>
      <div class="docker-line" v-if="portInfo.process_dir">
        <el-icon :size="14" color="#67c23a"><FolderOpened /></el-icon>
        <span class="label">目录:</span>
        <span class="value" :title="portInfo.process_dir">{{ portInfo.process_dir }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="card-actions">
      <template v-if="portInfo.status === 'RUNNING'">
        <el-button
          type="primary"
          class="open-btn"
          @click="openApp"
        >
          <el-icon style="margin-right: 4px"><TopRight /></el-icon>
          打开应用
        </el-button>
        <a
          :href="portInfo.url"
          target="_blank"
          rel="noopener noreferrer"
          class="hidden-link"
          ref="openLink"
        ></a>
      </template>
      <div v-else class="empty-tip">
        <el-icon :size="14" color="#909399"><InfoFilled /></el-icon>
        <span>端口未开放</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'PortCard',
  props: {
    portInfo: {
      type: Object,
      required: true
    },
    favorited: {
      type: Boolean,
      default: false
    }
  },
  emits: ['toggle-favorite'],
  setup(props) {
    const cardClass = computed(() => {
      return props.portInfo.status === 'RUNNING' ? 'card-running' : 'card-empty'
    })

    const statusClass = computed(() => {
      return props.portInfo.status === 'RUNNING' ? 'dot-running' : 'dot-empty'
    })

    const statusText = computed(() => {
      return props.portInfo.status === 'RUNNING' ? '运行中' : '空闲'
    })

    function openApp() {
      window.open(props.portInfo.url, '_blank', 'noopener,noreferrer')
    }

    return {
      cardClass,
      statusClass,
      statusText,
      openApp
    }
  }
}
</script>

<style scoped>
.port-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  border: 2px solid transparent;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  min-height: 150px;
}

/* 运行中卡片 */
.card-running {
  border-left: 4px solid #67c23a;
}

.card-running:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 18px rgba(103, 194, 58, 0.15);
}

/* 空闲卡片 */
.card-empty {
  border-left: 4px solid #dcdfe6;
  opacity: 0.85;
}

.card-empty:hover {
  border-color: #c0c4cc;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

/* 收藏态 */
.port-card.favorited {
  border-color: #E6A23C;
}

/* 头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.port-number {
  font-size: 26px;
  font-weight: 800;
  font-family: 'JetBrains Mono', Consolas, monospace;
  color: #303133;
  letter-spacing: 1px;
}

.card-empty .port-number {
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 4px;
}

/* 状态行 */
.status-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-running {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.6);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.dot-empty {
  background: #c0c4cc;
}

.status-text {
  font-size: 13px;
  color: #606266;
}

.card-empty .status-text {
  color: #909399;
}

.category-tag {
  margin-left: auto;
}

/* 应用名称 */
.app-name {
  font-size: 17px;
  font-weight: 700;
  color: #303133;
  margin-top: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-empty .app-name {
  color: #909399;
  font-weight: 500;
}

/* 备注 */
.app-remark {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Docker 信息 */
.docker-info {
  margin-top: 10px;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.docker-line {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.docker-line .label {
  color: #909399;
  flex-shrink: 0;
}

.docker-line .value {
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 进程信息（复用 docker-info 样式） */
.process-info {
  background: #f0f9eb;
}
.card-actions {
  margin-top: auto;
  padding-top: 12px;
}

.open-btn {
  width: 100%;
  border-radius: 8px;
  font-weight: 600;
}

.empty-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #909399;
  font-size: 13px;
  padding: 8px 0;
  background: #f5f7fa;
  border-radius: 8px;
}

.hidden-link {
  display: none;
}
</style>