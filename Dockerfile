# QuanPort — minimal image for reliable deployment
FROM python:3.11-slim

WORKDIR /app

# Light deps only - no Qiskit (avoids OOM on free tier)
COPY requirements-light.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py classical_optimizer.py quantum_optimizer.py data_fetcher.py ./
COPY static/ static/
COPY templates/ templates/

ENV PORT=8080
EXPOSE 8080

CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1