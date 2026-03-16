# builder stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# runtime stage
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=8080
USER appuser
CMD ["sh", "-c", "python -m flask --app app.main run --host 0.0.0.0 --port ${PORT}"]
