# syntax=docker/dockerfile:1

# --- Build stage ---
FROM python:3.13.12-alpine3.23 AS builder

RUN apk -U upgrade && \
    apk add --no-cache build-base gcc python3-dev mariadb-dev

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.13.12-alpine3.23

RUN apk -U upgrade && \
    apk add --no-cache mariadb-connector-c libcap openssl && \
    addgroup -S appgroup && \
    adduser -S appuser -G appgroup

COPY --from=builder /install /usr/local

WORKDIR /app

COPY src/ /app/

RUN mkdir -p /app/ssl && \
    chown appuser:appgroup /app/ssl

COPY --chown=appuser:appgroup ssl/www.ronroyce.dev.crt /app/ssl/www.ronroyce.dev.crt
COPY --chown=appuser:appgroup ssl/www.ronroyce.dev.key /app/ssl/www.ronroyce.dev.key

RUN chmod 644 /app/ssl/ssl/www.ronroyce.dev.crt && \
    chmod 600 ssl/www.ronroyce.dev.key 

# Allow non-root to bind port 443
RUN setcap 'cap_net_bind_service=+ep' $(which python3)

USER appuser

EXPOSE 443

CMD ["python3", "main.py"]
