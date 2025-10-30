# Dockerfile для деплоя на Amvera.ru
FROM python:3.12-slim

# Установка системных зависимостей для Playwright и OpenCV
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    # Для OpenCV
    libsm6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузеры Playwright (только chromium, без дополнительных зависимостей)
RUN playwright install --with-deps chromium

# Копируем весь код приложения
COPY . .

# Создаём необходимые директории
RUN mkdir -p logs screenshots browser_state

# Переменные окружения по умолчанию
ENV HEADLESS=true
ENV PORT=8000

# Открываем порт
EXPOSE 8000

# Запускаем API сервер
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
