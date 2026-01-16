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

# Cài curl và các dependencies cần thiết
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install dev requirements and run tests during build to catch regressions early
COPY requirements-dev.txt .
# Make running dev requirements and tests optional (default disabled).
# Set build arg RUN_TESTS=true to install dev deps and run pytest during image build.
ARG RUN_TESTS=false
RUN if [ -f requirements-dev.txt ] && [ "$RUN_TESTS" = "true" ]; then \
			pip install --no-cache-dir -r requirements-dev.txt && pytest -q; \
		else \
			echo "Skipping dev requirements and tests at build time (set RUN_TESTS=true to enable)"; \
		fi

COPY . .

# Cho phép import module theo cấu trúc
ENV PYTHONPATH=/app

EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
