FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg-dev zlib1g-dev libpng-dev libmariadb3 libmariadb-dev gcc \
    && rm -rf /var/lib/apt/lists/*


COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8080

CMD ["pip","install","uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
