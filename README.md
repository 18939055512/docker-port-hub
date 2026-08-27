# Docker Port Hub

Docker 内网开发服务端口导航管理平台

通过一个网页查看服务器上所有 Docker 应用端口状态，点击卡片直接打开对应应用，无需记忆 IP+端口。

![架构](https://img.shields.io/badge/架构-Vue3%20%2B%20Python%20Flask-brightgreen)
![版本](https://img.shields.io/badge/版本-v1.0.0-blue)

---

## 功能特性

- **端口扫描**：TCP 连接检测，默认扫描 38080-38599（可配置）
- **状态展示**：运行中（绿色）✅ / 空闲（灰色）⚪
- **Docker 自动识别**：自动获取容器名称、镜像名、端口映射
- **应用信息管理**：由服务器端 `ports.json` 维护（安全，不可网页修改）
- **实时搜索**：按端口号 / 应用名称 / Docker 容器名过滤
- **分类筛选**：开发工具 / 数据库 / Web / 运维 等
- **一键打开**：点击卡片自动拼接 `IP:端口` 在新标签页打开
- **收藏服务**：常用服务一键收藏
- **暗色模式**：支持明暗主题切换
- **响应式布局**：适配电脑浏览器

## 架构

```
┌──────────────┐     HTTP API      ┌──────────────────────┐
│  浏览器       │ ────────────────► │  Flask 后端 (Python)  │
│  Vue3 前端    │                   │                      │
│  Element Plus │                   │  ├ 端口扫描 (TCP)      │
└──────────────┘                   │  ├ Docker 检测         │
                                   │  └ 配置管理            │
                                   └──────────┬───────────┘
                                              │
                                         Docker 环境
```

## 项目结构

```
docker-port-hub
├── backend/                   # Python Flask 后端
│   ├── app.py                 # 主应用入口 + REST API
│   ├── scanner.py             # 端口扫描模块
│   ├── docker_detect.py       # Docker 容器检测模块
│   ├── config_manager.py      # 配置管理模块
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # Vue3 + Vite + Element Plus 前端
│   ├── src/
│   │   ├── views/Dashboard.vue      # 主页面
│   │   ├── components/PortCard.vue  # 端口卡片
│   │   └── api/index.js             # API 封装
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── config/                    # 配置文件（挂载进容器）
│   ├── application.yml        # 应用配置
│   └── ports.json             # 应用信息
├── docker-compose.yml
└── README.md
```

## 快速部署

### 1. 修改配置

编辑 `config/application.yml`：

```yaml
server:
  port: 38082              # 本平台访问端口

port:
  start: 38080             # 扫描起始端口
  end: 38599               # 扫描结束端口
  host: 127.0.0.1          # 扫描主机（本机）

access:
  prefix: http://192.0.2.10      # 示例地址；部署时替换为实际访问地址

scan:
  interval: 30             # 扫描周期（秒）
```

编辑 `config/ports.json` 添加应用说明：

```json
[
  {
    "port": 38080,
    "name": "Jenkins",
    "remark": "持续集成服务",
    "category": "开发工具"
  }
]
```

### 2. 启动

```bash
docker compose up -d --build
```

### 3. 访问

- 前端页面：`http://192.0.2.10:38082`
- 后端 API：`http://192.0.2.10:38082/api/ports`

## 配置说明

### application.yml

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `server.port` | 本平台后端端口 | 38082 |
| `port.start` | 扫描起始端口 | 38080 |
| `port.end` | 扫描结束端口 | 38599 |
| `port.host` | 扫描主机地址 | 127.0.0.1 |
| `access.prefix` | 应用访问前缀（IP） | http://127.0.0.1 |
| `scan.interval` | 扫描周期（秒） | 30 |

### ports.json

应用信息由服务器本地文件维护，不提供网页修改接口。

字段说明：

| 字段 | 说明 | 必填 |
|------|------|------|
| `port` | 端口号 | 是 |
| `name` | 应用名称 | 否 |
| `remark` | 应用描述 | 否 |
| `category` | 分类 | 否 |

## REST API

### 获取所有端口状态

```
GET /api/ports
```

响应：

```json
[
  {
    "port": 38080,
    "status": "RUNNING",
    "name": "Jenkins",
    "url": "http://192.0.2.10:38080",
    "docker": "ci-service",
    "image": "example/ci-service:latest",
    "container_status": "running",
    "remark": "持续集成服务",
    "category": "开发工具"
  }
]
```

### 搜索端口

```
GET /api/ports/search?keyword=jenkins
GET /api/ports/search?category=Web
GET /api/ports/search?status=RUNNING
```

### 获取配置

```
GET /api/config
```

### 获取统计

```
GET /api/stats
```

## 应用名称优先级

1. `ports.json` 中的配置
2. Docker 自动识别（容器名）
3. 未知应用

## 安全说明

本工具为内网开发服务导航，安全设计如下：

- 不提供网页修改端口功能
- 不提供网页执行 Shell / Docker 命令功能
- 不提供配置文件上传功能
- 配置文件仅由服务器本地维护
- 挂载的 docker.sock 为只读

## 开发模式

### 后端

```bash
cd backend
pip install -r requirements.txt
CONFIG_DIR=../config python app.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`（已配置 /api 代理到后端）。
