#!/bin/bash
# Скрипт для удаления неактуальных файлов проекта
# Дата: 23 ноября 2025

set -e

cd /root/vpn-server

echo "=== Очистка неактуальных файлов проекта ==="
echo ""

# Создаем архив перед удалением
ARCHIVE_DIR="archive"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_FILE="$ARCHIVE_DIR/unused_files_${TIMESTAMP}.tar.gz"

echo "📦 Создание архива неактуальных файлов..."
mkdir -p "$ARCHIVE_DIR"

# Список файлов для удаления
FILES_TO_REMOVE=(
    # Устаревшие анализы ключей
    "KEY_ANALYSIS_REPORT.md"
    "KEY_GENERATION_ANALYSIS.md"
    "KEY_ISSUE_ANALYSIS.md"
    "FINAL_KEY_DIAGNOSIS.md"
    "KEY_FIX_REPORT.md"
    
    # Устаревшие документы
    "CONFIG_GENERATION_EXPLAINED.md"
    "FINAL_IMPROVEMENTS_REPORT.md"
    "URL_NAME_FIX.md"
    "SCALING_TO_100_KEYS.md"
    
    # Анализы удаления файлов (после применения можно удалить)
    "FILES_TO_REMOVE_ANALYSIS.md"
    "REMOVE_FILES_SUMMARY.md"
    
    # Диагностические/тестовые Python скрипты
    "check_keys_internet_access.py"
    "check_specific_keys.py"
    "compare_urls.py"
    "deep_key_diagnosis.py"
    "fix_all_missing_publickey.py"
    "fix_key_publickey.py"
    "test_key_connection.py"
    "test_key_generation.py"
    "verify_and_fix_key.py"
)

# Проверяем существование файлов и добавляем в архив
EXISTING_FILES=()
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        EXISTING_FILES+=("$file")
    fi
done

if [ ${#EXISTING_FILES[@]} -eq 0 ]; then
    echo "✅ Нет файлов для удаления"
    exit 0
fi

echo "Найдено ${#EXISTING_FILES[@]} файлов для удаления"
echo ""

# Создаем архив
tar -czf "$ARCHIVE_FILE" "${EXISTING_FILES[@]}" 2>/dev/null || {
    echo "⚠️  Предупреждение: Не удалось создать архив, но продолжим удаление"
}

if [ -f "$ARCHIVE_FILE" ]; then
    ARCHIVE_SIZE=$(du -h "$ARCHIVE_FILE" | cut -f1)
    echo "✅ Архив создан: $ARCHIVE_FILE ($ARCHIVE_SIZE)"
else
    echo "⚠️  Архив не создан, но продолжим удаление"
fi

echo ""
echo "🗑️  Удаление файлов..."

# Удаляем файлы
REMOVED_COUNT=0
for file in "${EXISTING_FILES[@]}"; do
    if rm -f "$file"; then
        echo "  ✅ Удален: $file"
        ((REMOVED_COUNT++))
    else
        echo "  ❌ Ошибка при удалении: $file"
    fi
done

echo ""
echo "=== Итоги ==="
echo "Удалено файлов: $REMOVED_COUNT из ${#EXISTING_FILES[@]}"
if [ -f "$ARCHIVE_FILE" ]; then
    echo "Архив сохранен: $ARCHIVE_FILE"
fi
echo ""
echo "✅ Очистка завершена"

