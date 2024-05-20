# Указываем базовый образ
FROM postgres:15

# Задаем переменные окружения для базы данных
ENV POSTGRES_USER=${POSTGRES_USER}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
ENV POSTGRES_DB=${POSTGRES_DB}

# Копируем скрипты инициализации
COPY init.sql /docker-entrypoint-initdb.d/

# Задаем порт, который будет прослушивать контейнер
EXPOSE 5432

