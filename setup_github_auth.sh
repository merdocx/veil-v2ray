#!/bin/bash

# Скрипт настройки аутентификации GitHub
# Использование: ./setup_github_auth.sh <your-github-token>

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка аргументов
if [ $# -eq 0 ]; then
    print_error "Необходимо указать GitHub токен!"
    echo "Использование: $0 <your-github-token>"
    echo ""
    echo "Пример:"
    echo "  $0 github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    exit 1
fi

GITHUB_TOKEN="$1"
REPO_URL="https://github.com/merdocx/veil-v2ray.git"

print_info "Настройка аутентификации GitHub..."

# Проверка формата токена
if [[ ! "$GITHUB_TOKEN" =~ ^github_pat_ ]]; then
    print_warning "Токен не соответствует формату Fine-grained token (должен начинаться с 'github_pat_')"
    print_warning "Продолжаем настройку..."
fi

# Настройка Git
print_info "Настройка Git конфигурации..."

# Установка URL репозитория с токеном
git remote set-url origin "https://${GITHUB_TOKEN}@github.com/merdocx/veil-v2ray.git"

# Настройка credential helper
git config --global credential.helper store

# Создание файла с учетными данными
print_info "Создание файла учетных данных..."
cat > ~/.git-credentials << EOF
https://${GITHUB_TOKEN}@github.com
EOF

# Настройка Git пользователя (если не настроен)
if [ -z "$(git config --global user.name)" ]; then
    print_info "Настройка Git пользователя..."
    git config --global user.name "VPN Server"
    git config --global user.email "vpn@veil-bird.ru"
fi

# Тестирование подключения
print_info "Тестирование подключения к GitHub..."
if git ls-remote origin > /dev/null 2>&1; then
    print_success "Подключение к GitHub успешно!"
else
    print_error "Ошибка подключения к GitHub!"
    print_error "Проверьте правильность токена и права доступа"
    exit 1
fi

# Проверка статуса репозитория
print_info "Проверка статуса репозитория..."
cd /root/vpn-server
git status

print_success "Настройка аутентификации завершена!"
print_info "Теперь вы можете использовать:"
echo "  git push origin main          # Загрузка изменений"
echo "  git tag v2.1.5               # Создание тега"
echo "  git push origin v2.1.5       # Загрузка тега"
echo "  git push --tags              # Загрузка всех тегов"

print_warning "Токен сохранен в ~/.git-credentials"
print_warning "Убедитесь, что этот файл защищен от несанкционированного доступа!"



