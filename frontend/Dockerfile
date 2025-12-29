# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Instalar herramientas de red
RUN apk add --no-cache curl ca-certificates

# Configurar npm para mejor rendimiento y mostrar progreso
RUN npm config set fetch-retries 10 && \
    npm config set fetch-retry-mintimeout 30000 && \
    npm config set fetch-retry-maxtimeout 300000 && \
    npm config set progress true && \
    npm config set loglevel info && \
    npm config set registry https://registry.npmjs.org/

COPY package*.json ./
# Install dependencies con progreso visible
# Si existe package-lock.json, usa npm ci (más rápido y determinista)
# Si no existe, usa npm install con flags para mostrar progreso
RUN if [ -f package-lock.json ]; then \
        npm ci --legacy-peer-deps --progress=true; \
    else \
        npm install --legacy-peer-deps --progress=true --loglevel=info; \
    fi

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
