FROM python:3-alpine

RUN adduser -D -u 1000 calculate
WORKDIR /app

# Копирование файлов проекта в контейнер
COPY calculate/* /app/

RUN chown -R calculate:calculate /app

USER calculate

RUN pip install --no-warn-script-location --no-cache-dir requests aiohttp pytest pytest-asyncio allure-pytest

CMD ["python", "taiga.py"]
