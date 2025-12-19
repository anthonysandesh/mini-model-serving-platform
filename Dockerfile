FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt constraints.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY . /app
ENV PYTHONPATH=/app/src
RUN pip install -e .

ENV MMSC_CONFIG=/app/configs/platform.yaml

EXPOSE 8000

CMD ["uvicorn", "mmsp.serving.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
