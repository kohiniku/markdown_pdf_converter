FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install -g pnpm
RUN pnpm install

COPY . .

# No EXPOSE to avoid implying default port
CMD ["sh", "-c", "PORT=${PORT:?PORT not set} pnpm start"]
