FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
# npm install (no ci) porque el lockfile se mantiene desde macOS y no
# incluye las deps optional Linux-only de @tailwindcss/oxide (@emnapi/*)
RUN npm install --no-audit --prefer-offline --no-fund

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q -O- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
