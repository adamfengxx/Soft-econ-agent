# ── 阶段1：构建 React 应用 ──────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# ── 阶段2：nginx 静态服务 ────────────────────────────────────────────────────
FROM nginx:alpine

# 把构建产物放入 nginx 默认目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 使用自定义 nginx 配置（含 /api 反代）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
