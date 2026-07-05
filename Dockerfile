FROM python:3.11-slim

WORKDIR /app

# Upgrade pip and copy only requirements first (Docker Cache Optimization)
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .

# Install all dependencies from our single source of truth
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Create the data directory for our SQLite checkpoint persistent state
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]