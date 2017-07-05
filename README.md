# Hyperdash Python SDK

The Hyperdash Python SDK is the official SDK for [Hyperdash.io](https://hyperdash.io). Once installed, the SDK automatically monitors your machine learning jobs.

## Installation

`pip install --upgrade pip && pip install hyperdash`

## Usage

Import the monitor function, and apply it as a decorator to a function that runs your machine learning job. The only argument you need to pass to the monitor function is the name of the model that you're training.

```
# test_script.py

from hyperdash.sdk import monitor

@monitor("dogs vs. cats")
def train_dogs_vs_cats():
  print("Epoch 1, accuracy: 50%")
  time.sleep(2)
  print("Epoch 2, accuracy: 75%")
  time.sleep(2)
  print("Epoch 3, accuracy: 100%")
```

Once you've imported our library, make sure your API key is available in the HYPERDASH_API_KEY environment variable and run your program as you normally would:

`HYPERDASH_API_KEY=ZHNmYWRzYXNkZmFzZGZhc2RmYXNmYXNmFmZHNhZhcw== python test_script.py`

That's it! Open the Hyperdash mobile app and you should see your logs start to stream in!

Don't have an API key? Run `hyperdash signup` to get one!
