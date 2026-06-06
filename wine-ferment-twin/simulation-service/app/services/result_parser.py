from pathlib import Path
import pandas as pd


VARIABLE_CANDIDATES = {
    "hour": ["time"],
    "brix": ["brix"],
    "alcohol": ["alcohol"],
    "co2": ["co2"],
    "progress": ["progress"],
    "quality_score": ["qualityScore"],
    "risk_code": ["riskCode"],
}


def _find_col(df, names):
    for name in names:
        if name in df.columns:
            return name
    for column in df.columns:
        for name in names:
            if column.endswith("." + name) or column.strip('"').endswith("." + name) or column.strip('"') == name:
                return column
    raise KeyError(f"Cannot find any of columns {names}. Existing columns: {list(df.columns)[:20]}")


def parse_csv(csv_path: Path):
    df = pd.read_csv(csv_path)
    df = df.drop_duplicates(subset=[_find_col(df, VARIABLE_CANDIDATES["hour"])], keep="first")
    points = []
    cols = {key: _find_col(df, names) for key, names in VARIABLE_CANDIDATES.items()}
    for _, row in df.iterrows():
        points.append({
            "hour": float(row[cols["hour"]]),
            "brix": round(float(row[cols["brix"]]), 3),
            "alcohol": round(float(row[cols["alcohol"]]), 3),
            "co2": round(float(row[cols["co2"]]), 2),
            "progress": round(float(row[cols["progress"]]), 2),
            "quality_score": round(float(row[cols["quality_score"]]), 2),
            "risk_code": int(round(float(row[cols["risk_code"]]))),
        })
    return points
