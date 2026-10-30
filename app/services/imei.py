def valid_imei(imei: str) -> bool:
    """15 digits + Luhn check digit."""
    if not (imei and imei.isdigit() and len(imei) == 15):
        return False
    total = 0
    for i, ch in enumerate(reversed(imei)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9: d -= 9
        total += d
    return total % 10 == 0
