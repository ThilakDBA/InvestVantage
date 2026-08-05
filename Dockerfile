FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system investvantage \
    && adduser --system \
        --ingroup investvantage \
        --home /home/investvantage \
        --no-create-home \
        investvantage \
    && mkdir -p /home/investvantage/.streamlit \
    && chown -R investvantage:investvantage /home/investvantage
    
COPY pyproject.toml ./
COPY app ./app
COPY config ./config
COPY dashboard ./dashboard
COPY .streamlit ./.streamlit
COPY alembic.ini ./
COPY migrations ./migrations

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN mkdir -p /app/data \
    && chown -R investvantage:investvantage /app

USER investvantage

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
