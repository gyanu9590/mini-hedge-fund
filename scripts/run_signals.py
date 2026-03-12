from pathlib import Path
from importlib_metadata import files
import pandas as pd
from src.model.ml_model import train_model, generate_predictions # type: ignore

DATA_FEATURES = Path("data/features")
OUT_SIGNALS = Path("data/signals/signals.parquet")

def main():

    files = list(DATA_FEATURES.glob("*_features.parquet"))

    if len(files) == 0:
        print("No feature files found; no signals written.")
        return

    frames = []

    for f in files:

        df = pd.read_parquet(f)

        model = train_model(df)

        df = generate_predictions(df, model)

        df["signal"] = 0
        df.loc[df["prediction"] == 1, "signal"] = 1
        df.loc[df["prediction"] == 0, "signal"] = -1

        frames.append(df)


    if __name__ == "__main__":
        main()