# Use a slim Python base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy only requirements and install first (cache efficiency)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn
RUN pip install gunicorn

# Copy the rest of your application
COPY . .

# Expose the port your app will run on
EXPOSE 5000

# Run with Gunicorn (4 workers)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
