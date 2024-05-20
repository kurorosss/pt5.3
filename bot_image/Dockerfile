# Используйте официальный образ Python в качестве базового
FROM python:3.9-slim

# Установите зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Установите рабочую директорию в контейнере
WORKDIR /app

# Скопируйте файл requirements.txt в контейнер
COPY requirements.txt .

# Установите зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте исходный код приложения в контейнер
COPY . .

# Укажите команду для запуска вашего приложения
CMD ["python", "bot.py"]
