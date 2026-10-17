"""Безопасный генератор паролей (использует secrets)."""
import secrets
import string


def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    if length < 4:
        raise ValueError("Длина пароля должна быть не менее 4 символов")

    pools = []
    required = []
    if use_upper:
        pools.append(string.ascii_uppercase); required.append(secrets.choice(string.ascii_uppercase))
    if use_lower:
        pools.append(string.ascii_lowercase); required.append(secrets.choice(string.ascii_lowercase))
    if use_digits:
        pools.append(string.digits); required.append(secrets.choice(string.digits))
    if use_symbols:
        symbols = "!@#$%^&*()-_=+[]{};:,.<>?/|"
        pools.append(symbols); required.append(secrets.choice(symbols))

    if not pools:
        raise ValueError("Выберите хотя бы один тип символов")

    alphabet = "".join(pools)
    # Гарантируем наличие хотя бы одного из каждой категории
    rest = [secrets.choice(alphabet) for _ in range(length - len(required))]
    result = required + rest
    secrets.SystemRandom().shuffle(result)
    return "".join(result[:length])


def password_strength(password: str) -> str:
    """Грубая оценка надёжности."""
    if len(password) < 8:
        return "Очень слабый"
    score = 0
    if len(password) >= 12: score += 1
    if len(password) >= 16: score += 1
    if any(c.islower() for c in password): score += 1
    if any(c.isupper() for c in password): score += 1
    if any(c.isdigit() for c in password): score += 1
    if any(not c.isalnum() for c in password): score += 1

    if score <= 2: return "Слабый"
    if score <= 4: return "Средний"
    if score <= 5: return "Сильный"
    return "Очень сильный"