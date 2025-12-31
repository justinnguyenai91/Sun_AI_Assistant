# ===========================
# FRONTEND DOCKERFILE
# ===========================
# FROM node:20-alpine

# WORKDIR /app

# COPY package*.json ./
# RUN npm install

# COPY . .

# # Chế độ DEV để auto reload
# EXPOSE 5173
# CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
# ========== Stage 1: Build ==========
FROM node:18 AS builder
WORKDIR /app

# Copy dependencies files
COPY package*.json ./
RUN npm install

# Copy toàn bộ source code
COPY . .

# Build Vite (ra thư mục dist)
RUN npm run build


# ========== Stage 2: NGINX Serve ==========
FROM nginx:alpine

# Copy build output từ stage build vào NGINX public
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
