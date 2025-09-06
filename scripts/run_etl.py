# src/data/etl.py
from pathlib import Path
import pandas as pd
import numpy as np
import duckdb

def ingest_prices(symbols, out_dir):
    """
    Demo ETL that writes one parquet per symbol and creates a DuckDB view 'prices'.
    Produces longer synthetic history for development (250 business days).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for s in symbols:
        # 250 business days of synthetic prices (more realistic for z-score lookbacks)
        n = 250
        dates = pd.date_range("2023-01-01", periods=n, freq="B")
        # geometric random walk with small drift
        returns = 0.0005 + 0.01 * np.random.randn(n) * 0.1
        price = 100 * (1 + returns).cumprod()
        df = pd.DataFrame({"date": dates, "close": price})
        df.to_parquet(out / f"{s.replace(':','_')}.parquet", index=False)

    # create DuckDB view that reads all parquet files
    con = duckdb.connect(database=":memory:", read_only=False)
    sql = f"CREATE OR REPLACE VIEW prices AS SELECT * FROM read_parquet('{out.as_posix()}/*.parquet');"
    con.execute(sql)
    con.close()
