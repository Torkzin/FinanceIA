FROM node:24-alpine AS dependencies
WORKDIR /workspace
COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm install

FROM dependencies AS development
COPY apps/web ./apps/web
EXPOSE 3000
CMD ["npm", "run", "dev:web"]

FROM dependencies AS builder
COPY apps/web ./apps/web
RUN npm run build:web

FROM node:24-alpine AS production
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/public ./apps/web/public
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "apps/web/server.js"]

