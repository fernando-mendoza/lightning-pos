FROM mcr.microsoft.com/playwright:v1.59.1-jammy

WORKDIR /work

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY playwright.config.ts ./
COPY tests/ ./tests/

CMD ["pnpm", "exec", "playwright", "test"]
