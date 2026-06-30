import pandas as pd

def read_if_exists(path):
    if path.exists():
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda col: col.str.strip())
        return df
    return None
