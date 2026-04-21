FROM mcr.microsoft.com/playwright:v1.59.1-jammy

WORKDIR /work

COPY package.json ./
RUN npm install --no-audit --no-fund

COPY playwright.config.ts ./
COPY tests/ ./tests/

CMD ["npx", "playwright", "test"]
