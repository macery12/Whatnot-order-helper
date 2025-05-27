FROM python:3.11-slim

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy main files
COPY app.py .
COPY database.py .
COPY csv_decoder.py .
COPY scan_routes.py .
COPY admin_routes.py .

# Copy folders explicitly
COPY templates/ templates/
COPY static/ static/
COPY instance/ instance/

# Optional: Debug output (remove later if not needed)
RUN echo "STATIC CONTENT:" && ls -al /app/static && \
    echo "TEMPLATE CONTENT:" && ls -al /app/templates

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]