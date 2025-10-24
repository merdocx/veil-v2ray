# 🔐 Настройка GitHub для VPN Server

**Версия:** 2.1.4  
**Дата:** 22 октября 2025

---

## 📋 **Предварительные требования**

- Аккаунт GitHub
- Репозиторий `veil-v2ray` создан
- Права администратора на репозиторий

---

## 🔑 **Шаг 1: Создание Fine-grained Personal Access Token**

### **1.1 Переход в настройки GitHub**
1. Откройте [GitHub.com](https://github.com)
2. Нажмите на свой аватар → **Settings**
3. В левом меню выберите **Developer settings**
4. Выберите **Personal access tokens** → **Fine-grained tokens**

### **1.2 Создание нового токена**
1. Нажмите **Generate new token**
2. Заполните форму:
   - **Token name:** `VPN-Server-Deploy`
   - **Expiration:** `1 year` (рекомендуется)
   - **Description:** `Deploy and manage VPN server releases`

### **1.3 Настройка доступа к репозиторию**
1. **Repository access:** выберите **Selected repositories**
2. Выберите репозиторий `merdocx/veil-v2ray`
3. **Permissions:** установите следующие права:
   - ✅ **Contents:** Read and write
   - ✅ **Metadata:** Read
   - ✅ **Pull requests:** Read and write
   - ✅ **Issues:** Read and write
   - ✅ **Actions:** Read
   - ✅ **Packages:** Read and write (опционально)

### **1.4 Создание токена**
1. Нажмите **Generate token**
2. **⚠️ ВАЖНО:** Скопируйте токен и сохраните в безопасном месте!
3. Токен будет выглядеть как: `github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## ⚙️ **Шаг 2: Настройка аутентификации**

### **2.1 Автоматическая настройка (рекомендуется)**
```bash
# Запустите скрипт настройки с вашим токеном
./setup_github_auth.sh github_pat_your_token_here
```

### **2.2 Ручная настройка**
```bash
# Настройка URL репозитория с токеном
git remote set-url origin "https://github_pat_your_token@github.com/merdocx/veil-v2ray.git"

# Настройка credential helper
git config --global credential.helper store

# Создание файла учетных данных
echo "https://github_pat_your_token@github.com" > ~/.git-credentials
```

---

## 🚀 **Шаг 3: Тестирование подключения**

### **3.1 Проверка подключения**
```bash
# Проверка подключения к GitHub
git ls-remote origin

# Проверка статуса репозитория
git status
```

### **3.2 Тестовая загрузка**
```bash
# Создание тестового коммита
echo "# Test commit" >> test.txt
git add test.txt
git commit -m "Test commit"
git push origin main

# Удаление тестового файла
git rm test.txt
git commit -m "Remove test file"
git push origin main
```

---

## 📦 **Шаг 4: Создание релизов**

### **4.1 Автоматическое создание релиза**
```bash
# Создание релиза с автоматической версией
./create_release.sh v2.1.5 "Исправления и улучшения"

# Создание релиза с описанием
./create_release.sh v2.1.6 "Новые функции мониторинга трафика"
```

### **4.2 Полное обновление и развертывание**
```bash
# Автоматическое обновление версии и создание релиза
./update_and_deploy.sh v2.1.7 "Автоматическое обновление"

# Или с автоматической версией
./update_and_deploy.sh
```

---

## 🔧 **Шаг 5: Настройка автоматических релизов**

### **5.1 Создание GitHub Actions (опционально)**
Создайте файл `.github/workflows/release.yml`:

```yaml
name: Create Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
```

### **5.2 Настройка секретов**
1. Перейдите в **Settings** → **Secrets and variables** → **Actions**
2. Добавьте секрет `GITHUB_TOKEN` с вашим токеном

---

## 📊 **Шаг 6: Управление релизами**

### **6.1 Просмотр релизов**
- **GitHub:** https://github.com/merdocx/veil-v2ray/releases
- **Командная строка:** `git tag -l`

### **6.2 Создание релиза через веб-интерфейс**
1. Перейдите на страницу релизов
2. Нажмите **Create a new release**
3. Выберите тег или создайте новый
4. Заполните заголовок и описание
5. Загрузите архив (если нужно)
6. Нажмите **Publish release**

---

## 🛠️ **Полезные команды**

### **Управление тегами**
```bash
# Создание тега
git tag -a v2.1.5 -m "Release v2.1.5"

# Загрузка тега
git push origin v2.1.5

# Загрузка всех тегов
git push --tags

# Удаление тега (локально)
git tag -d v2.1.5

# Удаление тега (с GitHub)
git push origin :refs/tags/v2.1.5
```

### **Управление ветками**
```bash
# Создание новой ветки
git checkout -b feature/new-feature

# Переключение на ветку
git checkout main

# Слияние ветки
git merge feature/new-feature

# Удаление ветки
git branch -d feature/new-feature
```

### **Откат изменений**
```bash
# Откат последнего коммита
git reset --soft HEAD~1

# Откат к определенному коммиту
git reset --hard <commit-hash>

# Принудительная загрузка (осторожно!)
git push --force origin main
```

---

## 🔒 **Безопасность**

### **Защита токена**
- ✅ Никогда не коммитьте токен в код
- ✅ Используйте файл `~/.git-credentials` с правами 600
- ✅ Регулярно обновляйте токен
- ✅ Используйте минимально необходимые права

### **Проверка прав доступа**
```bash
# Проверка текущих прав
git remote -v

# Проверка конфигурации
git config --list | grep credential
```

---

## 🚨 **Устранение неполадок**

### **Ошибка аутентификации**
```bash
# Очистка кэша учетных данных
git config --global --unset credential.helper
rm ~/.git-credentials

# Повторная настройка
./setup_github_auth.sh your_token_here
```

### **Ошибка прав доступа**
1. Проверьте права токена в GitHub
2. Убедитесь, что репозиторий выбран в настройках токена
3. Проверьте, что токен не истек

### **Ошибка загрузки**
```bash
# Проверка подключения
git ls-remote origin

# Проверка статуса
git status

# Принудительная синхронизация
git fetch origin
git reset --hard origin/main
```

---

## 📞 **Поддержка**

При возникновении проблем:
1. Проверьте логи: `git log --oneline -10`
2. Проверьте статус: `git status`
3. Проверьте подключение: `git ls-remote origin`
4. Обратитесь к [документации GitHub](https://docs.github.com/en/authentication)

---

**✅ Настройка завершена!** Теперь вы можете загружать релизы и обновления на GitHub.



