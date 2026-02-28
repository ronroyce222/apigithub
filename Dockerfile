# syntax=docker/dockerfile:1


FROM python:3.12.12-alpine3.23

RUN apk -U upgrade
RUN apk add  build-base gcc python3-dev mariadb-dev openssl

WORKDIR /app

COPY src/ /app
COPY requirements.txt /app

RUN pip install --no-cache-dir --user -r /app/requirements.txt

RUN pip freeze

EXPOSE 8080

CMD python3.12 main.py

#CMD gunicorn --workers=5 --bind 0.0.0.0:8080 --reload --worker-class uvicorn.workers.UvicornWorker main:app
