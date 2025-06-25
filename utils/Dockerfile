FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY genlogs_v2.py .

CMD ["python", "genlogs_v2.py", "--mode", "production", "--rate", "100", "--urls", "1000"]
