FROM node:22.16.0-alpine3.22
WORKDIR /app
COPY --chown=node:node server.js ./server.js
ENV NODE_ENV=production PORT=3000 BIND_HOST=0.0.0.0
USER node
EXPOSE 3000
CMD ["node", "server.js"]
