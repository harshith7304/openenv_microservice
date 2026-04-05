FROM python:3.10-slim

# Avoid writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire working directory
COPY . .

# Expose standard HF Space port
EXPOSE 7860

# Command to run the local server required by the hackathon submission validation
CMD ["uv", "run", "server", "--host", "0.0.0.0", "--port", "7860"]
