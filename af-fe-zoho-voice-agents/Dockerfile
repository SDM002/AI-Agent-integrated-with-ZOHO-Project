FROM node:22-alpine AS deps
WORKDIR /app

RUN apk add --no-cache openssl libcrypto3 libssl3 \
    && apk upgrade --no-cache

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --include=optional

FROM node:22-alpine AS builder
WORKDIR /app

RUN apk add --no-cache openssl libcrypto3 libssl3 \
    && apk upgrade --no-cache

COPY package.json package-lock.json ./
RUN npm ci --include=optional

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3001

RUN apk add --no-cache openssl libcrypto3 libssl3 \
    && apk upgrade --no-cache

RUN addgroup -S nextjs && adduser -S nextjs -G nextjs

COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

USER nextjs
EXPOSE 3001

CMD ["node", "server.js"]
