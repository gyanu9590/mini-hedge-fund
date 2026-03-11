import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

print("Starting Hedge Fund Pipeline")

def main():
    try:
        from scripts.run_etl import main as run_etl
        run_etl()
    except:
        print("ETL skipped")

    try:
        from scripts.run_features import main as run_features
        run_features()
    except:
        print("Features skipped")

    try:
        from scripts.run_signals import main as run_signals
        run_signals()
    except:
        print("Signals skipped")

    try:
        from scripts.run_orders import main as run_orders
        run_orders()
    except:
        print("Orders skipped")

    try:
        from scripts.run_backtest import main as run_backtest
        run_backtest()
    except:
        print("Backtest skipped")
    try:
        from apps.apps import run_dashboard as run_app
        run_app()
    except:
        print("Dashboard skipped")

if __name__ == "__main__":
    main()