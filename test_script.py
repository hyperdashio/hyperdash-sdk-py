import time
import sys
from hyperdash.sdk import monitor


@monitor(job_name="ml_model")
def main():
    print("Doing the machine learning...")
    time.sleep(1)
    print("accuracy: 0%")
    time.sleep(2)
    print("accuracy: 25%")
    time.sleep(2)
    print("accuracy: 50%")
    time.sleep(2)
    print("accuracy: 75%")
    time.sleep(2)
    print("accuracy: 100%")
    print("Noice")

main()
