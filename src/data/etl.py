from pathlib import Path
import pandas as pd
import duckdb

def ingest_prices(symbols, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # TODO: replace with real source
    for s in symbols:
        df = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=10), 'close': range(10)})
        df.to_parquet(out / f"{s.replace(':','_')}.parquet")
    duckdb.query("CREATE OR REPLACE VIEW prices AS SELECT * FROM read_parquet('{}/*.parquet');".format(out)).execute()
