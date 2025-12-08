FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verzeichnisse für Daten & Relay
ENV DATA_DIR=/data
ENV RELAY_OUT_DIR=/relay/out
ENV RELAY_IN_DIR=/relay/in

EXPOSE 8000

CMD ["uvicorn", "sheratan_core_v2.main:app", "--host", "0.0.0.0", "--port", "8000"]
