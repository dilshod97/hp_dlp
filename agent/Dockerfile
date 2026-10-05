FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core
COPY collectors ./collectors
COPY main.py .

# Konteynerda demo agent: faqat active_window (ekran yo'q, skrinshotsiz).
# Haqiqiy agent Windows kompyuterlarda ishlaydi, konteynerда emas.
CMD ["python", "main.py"]
