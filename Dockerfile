FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SECRET_KEY=protejaja-chave-docker

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY home /app/home
COPY run.py /app/run.py

RUN mkdir -p /app/db /app/backend/uploads

EXPOSE 5000

CMD ["python", "run.py"]