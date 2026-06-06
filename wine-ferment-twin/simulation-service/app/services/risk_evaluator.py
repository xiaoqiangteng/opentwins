def risk_label(code: int) -> str:
    return {0: "normal", 1: "warning", 2: "critical", 3: "finished"}.get(int(code), "unknown")


def estimated_completion(points):
    for point in points:
        if point["progress"] >= 98.0:
            return point["hour"]
    return None
