FROM python:3.11-slim

WORKDIR /app

# shared client library (build context = backend/bots/)
COPY shared /app/shared

# bot-specific files
COPY telegram/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram/bot.py ./bot.py

ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
