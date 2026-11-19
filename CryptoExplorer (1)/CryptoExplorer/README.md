# CryptoExplorer

Минималистичный Django-сайт для поиска криптовалют и блокчейн-сетей, просмотра рынка и чтения данных EVM-блокчейнов.

## Запуск в Omarchy Linux / Arch Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Откройте http://127.0.0.1:8000/

При следующих запусках:

```bash
cd ~/CryptoExplorer
source .venv/bin/activate
python manage.py runserver
```

## Возможности
- Поиск монет через CoinGecko.
- Поиск сетей и TVL через DefiLlama.
- Таблица 10 крупнейших криптовалют.
- Blockchain Interaction: текущая высота блока, публичный баланс EVM-адреса, поиск транзакции и просмотр блока.
- Поддерживаемые сети: Ethereum, BNB Chain, Polygon, Arbitrum One.

## Важные ограничения и безопасность
- Blockchain Interaction работает в режиме чтения через публичные RPC. Публичные узлы могут ограничивать частоту запросов или временно быть недоступны.
- Для баланса, транзакций и блоков нужен адрес/хеш/номер именно выбранной сети.
- Приватные ключи и seed-фразы не нужны и не должны вводиться в этот сайт.
- Отправка транзакций и подключение MetaMask пока не реализованы. Их безопаснее добавлять через браузерный кошелёк с подтверждением каждой операции, не передавая ключи Django-серверу.
- Рыночные данные зависят от лимитов сторонних API.
- Перед публичным развёртыванием выключите DEBUG, задайте новый SECRET_KEY, настройте ALLOWED_HOSTS, HTTPS, кеширование и production-сервер.
