def pm25_to_score(pm25):
    """
     Convert PM2.5 concentration (µg/m³) into a score 0–100.
    0 = sehr schlecht (≥75 µg/m³)
    100 = sehr gut (0 µg/m³)
    :param pm25:
    :return:
    """
    if pm25 is None:
        return 50
    score = max(0, min(100, int(100 - (pm25 / 75) * 100)))
    return score

