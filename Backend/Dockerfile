# # ===========================
# # BACKEND DOCKERFILE
# # ===========================
# FROM python:3.12-slim

# # giảm lỗi locale
# ENV PYTHONUNBUFFERED=1
# ENV PYTHONDONTWRITEBYTECODE=1

# WORKDIR /app

# COPY requirements.txt requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# EXPOSE 9000
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cho phép import module theo cấu trúc
ENV PYTHONPATH=/app

EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
