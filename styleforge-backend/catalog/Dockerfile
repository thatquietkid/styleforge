FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY catalog /app/catalog
RUN mkdir -p /app/uploads

EXPOSE 8002

CMD ["uvicorn", "catalog.main:app", "--host", "0.0.0.0", "--port", "8002"]
