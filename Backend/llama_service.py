import subprocess

def query_llama(prompt: str) -> str:
    command = [
        "./llama-cli",  # hoặc đường dẫn đầy đủ tới llama.cpp binary
        "-m", "./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "-p", prompt,
        "--n-predict", "256"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"
