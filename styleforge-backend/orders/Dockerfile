FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY orders /app/orders

EXPOSE 8003

CMD ["uvicorn", "orders.main:app", "--host", "0.0.0.0", "--port", "8003"]
