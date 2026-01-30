FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y build-essential \
    && pip install --no-cache-dir -r requirements.txt

# Copy new structure
COPY core/ core/
COPY services/ services/
COPY workers/ workers/
COPY main.py .



# Default command
CMD ["python", "main.py", "--type", "standard"]