import time
import subprocess
import sys

while True:

    subprocess.call([sys.executable, "scripts/run_all.py"])

    print("Waiting 5 minutes")

    time.sleep(300)