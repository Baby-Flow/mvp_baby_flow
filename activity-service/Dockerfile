FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Для отладки - показать файлы
RUN ls -la

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]