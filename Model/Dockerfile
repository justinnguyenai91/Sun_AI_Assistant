# FROM ghcr.io/ggerganov/llama.cpp:full

# WORKDIR /app

# # Copy model
# COPY qwen2-7b-instruct-q4_k_m.gguf /app/model.gguf

# # Run llama.cpp server
# EXPOSE 8080
# CMD ["llama-server", "-m", "model.gguf", "-c", "4096", "-ngl", "1", "--port", "8080"]
FROM ghcr.io/ggml-org/llama.cpp:full

WORKDIR /app

# Copy model
COPY qwen2-7b-instruct-q4_k_m.gguf /app/model.gguf

EXPOSE 8080

CMD ["--server", "-m", "model.gguf", "-c", "4096", "--threads", "8", "--host", "0.0.0.0", "--port", "8080"]