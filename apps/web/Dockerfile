FROM node:22-alpine AS deps
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG API_INTERNAL_URL=http://api:8000
ENV NEXT_TELEMETRY_DISABLED=1 API_INTERNAL_URL=$API_INTERNAL_URL
RUN pnpm build

FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S lds && adduser -S lds -G lds
COPY --from=build --chown=lds:lds /app/.next/standalone ./
COPY --from=build --chown=lds:lds /app/.next/static ./.next/static
COPY --from=build --chown=lds:lds /app/public ./public
USER lds
EXPOSE 3000
CMD ["node", "server.js"]
