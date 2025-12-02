# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY flowyml/ui/frontend/package.json flowyml/ui/frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY flowyml/ui/frontend ./

# Build the application
# We assume the build script produces artifacts in 'dist' or 'build'
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
