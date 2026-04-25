# syntax=docker/dockerfile:1
# Production: Vite minified `dist/` + nginx. Build from this directory: `docker build -t ... .`

FROM node:22-alpine AS build
WORKDIR /app

ENV npm_config_devdir=/tmp/node-gyp

# Baked at build: browser calls API on 10.0.0.46:<port> (set in deploy-orchestrator workflow)
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ > /dev/null || exit 1
