FROM node:22-alpine

RUN apk add --no-cache python3 make g++ && corepack enable
WORKDIR /workspace

COPY package.json pnpm-workspace.yaml turbo.json ./
COPY apps/api/package.json apps/api/package.json
RUN pnpm install --no-frozen-lockfile --filter @waste/api...

COPY apps/api apps/api
RUN pnpm --filter @waste/api build

WORKDIR /workspace/apps/api
ENV NODE_ENV=production
EXPOSE 4000
CMD ["node", "dist/main.js"]

