FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём папку static если нет
RUN mkdir -p static

EXPOSE 8080

CMD ["python", "bot.py"]
