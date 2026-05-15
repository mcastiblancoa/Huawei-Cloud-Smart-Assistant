import re
from typing import Any


def sanitize_string(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    return cleaned


def sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for key, value in params.items():
        clean_key = sanitize_string(str(key))
        if isinstance(value, str):
            sanitized[clean_key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[clean_key] = sanitize_params(value)
        elif isinstance(value, list):
            sanitized[clean_key] = [
                sanitize_string(v) if isinstance(v, str) else
                sanitize_params(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            sanitized[clean_key] = value
    return sanitized


def validate_service_name(service: str) -> str:
    cleaned = sanitize_string(service)
    if not cleaned:
        raise ValueError("Service name cannot be empty")
    if not re.match(r'^[A-Za-z][A-Za-z0-9_-]*$', cleaned):
        raise ValueError(f"Invalid service name: {cleaned}")
    return cleaned


def validate_operation_name(operation: str) -> str:
    cleaned = sanitize_string(operation)
    if not cleaned:
        raise ValueError("Operation name cannot be empty")
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', cleaned):
        raise ValueError(f"Invalid operation name: {cleaned}")
    return cleaned


def sanitize_model_reply(text: str, max_len: int = 16000) -> str:
    """Strip model/tokenizer garbage (private-use blocks, long punctuation runs) from chat replies."""
    import unicodedata

    if not text:
        return text
    t = unicodedata.normalize("NFC", text)
    out: list[str] = []
    for ch in t:
        o = ord(ch)
        cat = unicodedata.category(ch)
        if o in (0x200B, 0x200C, 0x200D, 0xFEFF):
            continue
        if 0xE000 <= o <= 0xF8FF or 0xF0000 <= o <= 0x10FFFD:
            continue
        if cat == "Cs" or (cat == "Cc" and ch not in "\n\t\r"):
            continue
        if cat == "Co" and o > 0xFFFF:
            continue
        out.append(ch)
    s = "".join(out)
    s = re.sub(r";amp(;|$)", "", s, flags=re.I)
    s = re.sub(r"(?:&amp;|&#x?[0-9a-fA-F]+;)", "", s)
    for pat, repl in (
        (r'(:|\\|/|#|-|\)|\.|\]){6,}', r'\1\1\1'),
        (r'[\xff]{4,}', ''),
        (r'[ÿ]{3,}', ''),
        (r'\\{5,}', ''),
        (r'[。]{6,}', '…'),
    ):
        s = re.sub(pat, repl, s)
    s = re.sub(r"\n{5,}", "\n\n\n\n", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s
