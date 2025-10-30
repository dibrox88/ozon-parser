"""
Генератор секретного ключа для API
Использование: python generate_api_key.py
"""

import secrets

def generate_api_key(length: int = 32) -> str:
    """
    Генерирует криптографически стойкий случайный ключ.
    
    Args:
        length: Длина ключа в байтах (по умолчанию 32)
    
    Returns:
        URL-безопасная base64 строка
    """
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    print("=" * 70)
    print("🔐 ГЕНЕРАТОР API SECRET KEY")
    print("=" * 70)
    print()
    
    # Генерируем несколько ключей разной длины
    keys = {
        "Короткий (16 байт)": generate_api_key(16),
        "Средний (32 байта, рекомендуется)": generate_api_key(32),
        "Длинный (64 байта)": generate_api_key(64),
    }
    
    for name, key in keys.items():
        print(f"{name}:")
        print(f"  {key}")
        print()
    
    print("=" * 70)
    print("📋 ИНСТРУКЦИЯ:")
    print("=" * 70)
    print()
    print("1. Скопируйте ключ (рекомендуется средний)")
    print("2. В Amvera добавьте переменную окружения:")
    print("   API_SECRET_KEY=<ваш_ключ>")
    print()
    print("3. В Google Apps Script замените:")
    print("   const API_SECRET_KEY = '<ваш_ключ>';")
    print()
    print("4. НИКОГДА не коммитьте этот ключ в Git!")
    print()
    print("=" * 70)
