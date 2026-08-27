# Docker Port Hub - 前端构建
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY package.json ./
RUN npm install

# 构建
COPY . .
RUN npm run build

# 生产环境
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]