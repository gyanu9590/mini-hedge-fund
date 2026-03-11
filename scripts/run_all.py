import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

def main():

    print("Starting Hedge Fund Pipeline")

    from scripts.run_etl import main as run_etl
    from scripts.run_features import main as run_features
    from scripts.run_signals import main as run_signals
    from scripts.run_orders import main as run_orders
    from scripts.run_backtest import main as run_backtest

    run_etl()
    run_features()
    run_signals()
    run_orders()
    run_backtest()

    print("Pipeline finished")


if __name__ == "__main__":
    main()