# Stage 1: Build Flutter Web app
FROM debian:bookworm-slim AS build-env

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    libglu1-mesa \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Disable SSL verification (temporary) and clone Flutter
RUN git config --global http.sslVerify false && \
    git clone https://github.com/flutter/flutter.git -b stable --depth 1 /usr/local/flutter

# Add Flutter to PATH
ENV PATH="/usr/local/flutter/bin:/usr/local/flutter/bin/cache/dart-sdk/bin:${PATH}"

# Configure Flutter
RUN flutter config --no-analytics && \
    flutter config --enable-web && \
    flutter doctor

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pubspec.yaml pubspec.lock ./

# Get Flutter packages
RUN flutter pub get

# Copy project
COPY . .

# Build Flutter Web
RUN flutter build web --release --dart-define=API_BASE_URL=/api

# Stage 2: Nginx
FROM nginx:alpine

COPY --from=build-env /app/build/web /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]