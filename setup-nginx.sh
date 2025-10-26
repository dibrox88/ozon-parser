#!/bin/bash
# Скрипт для настройки Nginx reverse proxy и SSL

set -e

echo "🔧 Настройка Nginx для Ozon Parser API..."

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Проверка наличия nginx
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}❌ Nginx не установлен!${NC}"
    echo "Установите nginx: sudo apt install nginx"
    exit 1
fi

# Запрос домена
echo -e "\n${YELLOW}Введите ваш домен (или IP адрес):${NC}"
read -r DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ Домен не указан!${NC}"
    exit 1
fi

# Создание конфигурации Nginx
echo -e "\n${YELLOW}📝 Создание конфигурации Nginx...${NC}"

sudo tee /etc/nginx/sites-available/ozon-parser-api > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    access_log /var/log/nginx/ozon-parser-api-access.log;
    error_log /var/log/nginx/ozon-parser-api-error.log;

    client_max_body_size 10M;

    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

echo -e "${GREEN}✓${NC} Конфигурация создана: /etc/nginx/sites-available/ozon-parser-api"

# Создание символической ссылки
echo -e "\n${YELLOW}🔗 Активация конфигурации...${NC}"
sudo ln -sf /etc/nginx/sites-available/ozon-parser-api /etc/nginx/sites-enabled/

# Удаление дефолтного сайта (опционально)
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    echo -e "${YELLOW}Удалить дефолтный сайт Nginx? (y/n)${NC}"
    read -r REMOVE_DEFAULT
    if [ "$REMOVE_DEFAULT" = "y" ]; then
        sudo rm /etc/nginx/sites-enabled/default
        echo -e "${GREEN}✓${NC} Дефолтный сайт удалён"
    fi
fi

# Проверка конфигурации
echo -e "\n${YELLOW}🔍 Проверка конфигурации Nginx...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✓${NC} Конфигурация корректна"
else
    echo -e "${RED}❌ Ошибка в конфигурации!${NC}"
    exit 1
fi

# Перезапуск Nginx
echo -e "\n${YELLOW}🔄 Перезапуск Nginx...${NC}"
sudo systemctl restart nginx
echo -e "${GREEN}✓${NC} Nginx перезапущен"

# Проверка SSL (Let's Encrypt)
echo -e "\n${YELLOW}Установить SSL сертификат (Let's Encrypt)? (y/n)${NC}"
read -r INSTALL_SSL

if [ "$INSTALL_SSL" = "y" ]; then
    # Установка certbot
    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}📦 Установка certbot...${NC}"
        sudo apt update
        sudo apt install -y certbot python3-certbot-nginx
    fi
    
    # Получение сертификата
    echo -e "\n${YELLOW}📜 Получение SSL сертификата...${NC}"
    echo "Введите ваш email для уведомлений:"
    read -r EMAIL
    
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} SSL сертификат установлен"
        echo -e "${GREEN}✓${NC} HTTPS включён автоматически"
        
        # Настройка автообновления
        echo -e "\n${YELLOW}🔄 Настройка автообновления сертификата...${NC}"
        sudo systemctl enable certbot.timer
        sudo systemctl start certbot.timer
        echo -e "${GREEN}✓${NC} Автообновление настроено"
    else
        echo -e "${RED}❌ Ошибка при получении SSL сертификата${NC}"
        echo "Проверьте, что:"
        echo "  - Домен $DOMAIN указывает на IP этого сервера"
        echo "  - Порт 80 открыт в firewall"
    fi
fi

echo -e "\n${GREEN}✅ Nginx настроен успешно!${NC}"
echo -e "\n${YELLOW}Информация:${NC}"
echo "  Домен: $DOMAIN"
echo "  HTTP: http://$DOMAIN"
if [ "$INSTALL_SSL" = "y" ]; then
    echo "  HTTPS: https://$DOMAIN"
fi
echo -e "\n${YELLOW}Проверка:${NC}"
echo "  curl http://$DOMAIN/health"
if [ "$INSTALL_SSL" = "y" ]; then
    echo "  curl https://$DOMAIN/health"
fi
