import time
import sys
import hyperdash as hd

@hd.monitor("test job a")
def main(hd_client):
    print("Doing the machine learning...")
    time.sleep(2)
    hd_client.metric("example metric",5)
    print("accuracy: 0%")
    time.sleep(2)
    hd_client.metric("example metric",8)
    hd_client.metric("another",432.432)
    print("accuracy: 25%")
    time.sleep(2)
    print("accuracy: 50%")
    time.sleep(2)
    print("accuracy: 75%")
    time.sleep(2)
    print("accuracy: 100%")

main()
