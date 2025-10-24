#!/bin/bash

# Скрипт автоматического обновления и развертывания
# Использование: ./update_and_deploy.sh [version] [description]

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

# Получение версии из аргументов или автоматическое определение
if [ $# -ge 1 ]; then
    VERSION="$1"
else
    # Автоматическое определение версии на основе даты
    VERSION="v2.1.$(date +%m%d)"
fi

DESCRIPTION="${2:-Automated update $VERSION}"

print_info "🚀 Автоматическое обновление и развертывание $VERSION"

# Переход в директорию проекта
cd /root/vpn-server

# Проверка аутентификации GitHub
print_info "Проверка аутентификации GitHub..."
if ! git ls-remote origin > /dev/null 2>&1; then
    print_error "Ошибка аутентификации GitHub!"
    print_info "Запустите сначала: ./setup_github_auth.sh <your-token>"
    exit 1
fi

# Обновление версии в файлах
print_info "Обновление версии в файлах..."

# Обновление README.md
if [ -f "README.md" ]; then
    sed -i "s/\*\*Версия:\*\* [0-9.]*/\*\*Версия:\*\* ${VERSION#v}/" README.md
    sed -i "s/\*\*Дата обновления:\*\* [0-9]* [а-я]* [0-9]*/\*\*Дата обновления:\*\* $(date +'%d %B %Y')/" README.md
fi

# Обновление requirements.txt
if [ -f "requirements.txt" ]; then
    sed -i "s/# Версия: [0-9.]*/# Версия: ${VERSION#v}/" requirements.txt
    sed -i "s/# Дата: [0-9-]*/# Дата: $(date +%Y-%m-%d)/" requirements.txt
fi

# Обновление API документации
if [ -f "API_DOCUMENTATION.md" ]; then
    sed -i "s/\*\*Версия API:\*\* [0-9.]*/\*\*Версия API:\*\* ${VERSION#v}/" API_DOCUMENTATION.md
fi

# Сохранение изменений
print_info "Сохранение изменений..."
git add -A

# Проверка, есть ли изменения для коммита
if [ -z "$(git status --porcelain)" ]; then
    print_warning "Нет изменений для коммита"
else
    git commit -m "🚀 $VERSION: $DESCRIPTION"
    print_success "Изменения сохранены"
fi

# Загрузка изменений
print_info "Загрузка изменений на GitHub..."
git push origin main

# Создание релиза
print_info "Создание релиза $VERSION..."
./create_release.sh "$VERSION" "$DESCRIPTION"

print_success "✅ Обновление и развертывание завершено!"
print_info "Версия: $VERSION"
print_info "Описание: $DESCRIPTION"
print_info "Репозиторий: https://github.com/merdocx/veil-v2ray"
print_info "Релизы: https://github.com/merdocx/veil-v2ray/releases"



