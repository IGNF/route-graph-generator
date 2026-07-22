import pandas as pd
from pathlib import Path

def read_if_exists(path_or_buf):
    if hasattr(path_or_buf, "read"):
        df = pd.read_csv(path_or_buf, dtype=str, keep_default_na=False)
    else:
        path = Path(path_or_buf)
        if not path.exists():
            return None
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = df.columns.str.strip()
    df = df.apply(lambda col: col.str.strip())
    return df
