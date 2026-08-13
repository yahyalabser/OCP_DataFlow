FROM python:3.11.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

COPY src/ .

RUN useradd --create-home --uid 1000 etluser \
    && chown -R etluser:etluser /app
USER etluser

CMD ["python", "run_etl.py"]