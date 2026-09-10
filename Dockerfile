FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /app/data /app/output && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "compliance_intelligence.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

