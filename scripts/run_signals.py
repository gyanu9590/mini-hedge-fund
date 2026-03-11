from pathlib import Path
import pandas as pd

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

        df["signal"] = 0
        df.loc[df["momentum_5"] > 0, "signal"] = 1
        df.loc[df["momentum_5"] < 0, "signal"] = -1

        frames.append(df)

    signals = pd.concat(frames)

    OUT_SIGNALS.parent.mkdir(parents=True, exist_ok=True)
    signals.to_parquet(OUT_SIGNALS, index=False)

    print("Signals generated")


if __name__ == "__main__":
    main()