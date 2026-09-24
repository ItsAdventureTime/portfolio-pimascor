FROM node:alpine AS build

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig*.json vite.config.ts ./
COPY public ./public
COPY src ./src

ARG VITE_BASE_PATH=/
ARG VITE_API_URL=/api/v1
ARG VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_csrf
ARG VITE_DEPLOYMENT_TIER=production
ENV VITE_BASE_PATH=$VITE_BASE_PATH VITE_API_URL=$VITE_API_URL VITE_CSRF_COOKIE_NAME=$VITE_CSRF_COOKIE_NAME VITE_DEPLOYMENT_TIER=$VITE_DEPLOYMENT_TIER
RUN npm run build

FROM nginx:alpine
COPY nginx.compose.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 8080
