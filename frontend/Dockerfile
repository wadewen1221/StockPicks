# 前端 Dockerfile（多阶段构建：先 build，再 serve）
# Stage 1: 构建 Vue 静态资源
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖清单
COPY package*.json ./

# 安装依赖（npm ci 严格按 lock 文件）
RUN npm ci --no-audit --no-fund

# 复制源码
COPY . .

# 构建生产包
RUN npm run build

# Stage 2: 用 nginx serve 静态文件
FROM nginx:1.27-alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]