#!/bin/sh
set -e

# Генерируем конфиг с переменной окружения
mkdir -p /extensions/buttons/src/
echo "export const API_ENDPOINT = '${LLM_VALIDATOR_URL}';" > /extensions/buttons/src/config.ts

# Переходим в рабочую директорию
cd /extensions/buttons

# Пересобираем расширение с новым конфигом
npm install
npm run build
jupyter labextension install .

# Запускаем основной процесс (CMD из базового образа)
exec "$@"