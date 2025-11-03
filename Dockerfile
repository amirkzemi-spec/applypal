# Use official Python base image
FROM python:3.11-slim

# Install ffmpeg (for voice/audio generation)
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project
COPY . .

# Expose a port (Render expects one even if unused)
EXPOSE 8000

# Run the bot
CMD ["python", "main.py"]
