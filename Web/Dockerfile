FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server ./server
COPY ui ./ui
COPY run.sh .
COPY pipelines ./pipelines

# Make run.sh executable
RUN chmod +x /app/run.sh

EXPOSE 5001

CMD ["/app/run.sh", "--port", "5001"]
