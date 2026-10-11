FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV STORE=/data/store MANIFESTS=/data/manifests

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ api/
COPY ib_scrape/ ib_scrape/
COPY ui/ ui/
COPY manifests/ /data/manifests/

VOLUME /data/store
EXPOSE 8471
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8471"]
