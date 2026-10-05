# 1-bosqich: React ilovani build qilish
FROM node:20-slim AS build
WORKDIR /app
# Docker'da API same-origin bo'lsin (nginx uzatadi) — bo'sh BASE
ARG VITE_API_BASE=""
ENV VITE_API_BASE=$VITE_API_BASE
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# 2-bosqich: statik fayllarni nginx orqali tarqatish
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
