#!/bin/bash

# Скрипт создания релиза на GitHub
# Использование: ./create_release.sh <version> <description>

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
if [ $# -lt 1 ]; then
    print_error "Необходимо указать версию релиза!"
    echo "Использование: $0 <version> [description]"
    echo ""
    echo "Примеры:"
    echo "  $0 v2.1.5"
    echo "  $0 v2.1.5 \"Исправления и улучшения\""
    echo "  $0 v2.1.5 \"Новые функции мониторинга трафика\""
    exit 1
fi

VERSION="$1"
DESCRIPTION="${2:-Release $VERSION}"

print_info "Создание релиза $VERSION..."

# Переход в директорию проекта
cd /root/vpn-server

# Проверка, что мы в git репозитории
if [ ! -d ".git" ]; then
    print_error "Не найден git репозиторий!"
    exit 1
fi

# Проверка статуса репозитория
print_info "Проверка статуса репозитория..."
if [ -n "$(git status --porcelain)" ]; then
    print_warning "Обнаружены несохраненные изменения!"
    print_info "Сохраняем изменения..."
    git add -A
    git commit -m "🚀 $VERSION: $DESCRIPTION"
fi

# Проверка, что все изменения загружены
print_info "Проверка синхронизации с GitHub..."
git fetch origin
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    print_warning "Локальные изменения не синхронизированы с GitHub!"
    print_info "Загружаем изменения..."
    git push origin main
fi

# Создание тега
print_info "Создание тега $VERSION..."
if git tag -l | grep -q "^$VERSION$"; then
    print_warning "Тег $VERSION уже существует!"
    print_info "Удаляем существующий тег..."
    git tag -d "$VERSION"
    git push origin :refs/tags/"$VERSION"
fi

git tag -a "$VERSION" -m "$DESCRIPTION"

# Загрузка тега
print_info "Загрузка тега на GitHub..."
git push origin "$VERSION"

# Создание архива для релиза
print_info "Создание архива релиза..."
ARCHIVE_NAME="vpn-server-$VERSION.tar.gz"
tar --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    -czf "/tmp/$ARCHIVE_NAME" .

print_success "Релиз $VERSION создан успешно!"
print_info "Архив создан: /tmp/$ARCHIVE_NAME"
print_info "Тег загружен: $VERSION"

echo ""
print_info "Для создания релиза на GitHub:"
echo "1. Перейдите на https://github.com/merdocx/veil-v2ray/releases"
echo "2. Нажмите 'Create a new release'"
echo "3. Выберите тег: $VERSION"
echo "4. Заголовок: $VERSION"
echo "5. Описание: $DESCRIPTION"
echo "6. Загрузите архив: /tmp/$ARCHIVE_NAME"
echo "7. Нажмите 'Publish release'"

print_info "Или используйте GitHub CLI (если установлен):"
echo "gh release create $VERSION /tmp/$ARCHIVE_NAME --title '$VERSION' --notes '$DESCRIPTION'"
