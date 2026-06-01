FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY auth /app/auth

EXPOSE 8001

CMD ["uvicorn", "auth.main:app", "--host", "0.0.0.0", "--port", "8001"]
