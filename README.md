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

### API key storage

If you signed up with the CLI, the Hyperdash CLI will automatically install your API key in a hyperdash.json file in the home directory for you user.

You can alternatively override this API key with a hyperdash.json file in your local directory (so you can have different API keys for different projects) or with the HYPERDASH_API_KEY environment variable.

Finally, the monitor function accepts an api_key_getter argument that if passed in will be called everytime we need to retrieve your API key. Example:

```
# test_script.py

from hyperdash.sdk import monitor

# This function can do anything you want, as long as it returns a Hyperdash API key as a string
def get_api_key():
  return "super_secret_api_key"

@monitor("dogs vs. cats", api_key_getter=get_api_key)
def train_dogs_vs_cats():
  print("Epoch 1, accuracy: 50%")
  time.sleep(2)
  print("Epoch 2, accuracy: 75%")
  time.sleep(2)
  print("Epoch 3, accuracy: 100%")
```

Keep in mind that we will call your function on a regular basis while the job is running (currently about once every 5 minutes) so that we can support API key rotation for long-running jobs.

### API Key Rotation

The Hyperdash library will try and load up your API key about once every 5 minutes. Generally speaking this isn't something you need to think about, but in the rare case that you need to rotate an API key without stopping a long-running job, you can just change the HYPERDASH_API_KEY environment variable or hyperdash.json file and the SDK will automatically pickup the new key within a few minutes.