# Hyperdash Python SDK

Hyperdash is a machine learning monitoring library, written in Python and capable of running alongside Tensorflow, Scikit-Learn, and other modelling libraries. It was developed with a focus on enabling fast knowledge gain.

Use Hyperdash if you need model monitoring that:

* Tracks your hyperparmeters across different model experiments.
* Graphs performance metrics (loss, reward, etc.) in real-time.
* Can be viewed remotely via both a web and mobile app.
* Notifies you when your experiment job has finished.

Hyperdash is compatible with: **Python 2.7-3.6**

[Visualization gif here]


## Installation

```
$ pip install --upgrade pip && pip install hyperdash
```
Installing within a python virtual environment such as [**virtualenv**](https://github.com/pypa/virtualenv) or [**conda**](https://github.com/conda/conda) is recommended.
```
# Login if you have an account
$ hyperdash login

# Or signup free with an email
$ hyperdash signup
```
After `login` or `signup`, an API key is saved to your local machine for automatic authorization. If you'd rather manage your API key manually, then review the "API Key Storage" section below.

You're ready to use Hyperdash!

## Getting started: 30 seconds
The core object of Hyperdash is the **Experiment**. The simplest experiment logs a single print statement.
```
from hyperdash import Experiment

# Create and start an experiment with a model name
exp = Experiment("Print Example")

print("View me on web or mobile")

# cleanup
exp.end()
```
This outputs something like:
```
View me on web or mobile
Logs for this run of Print Example are available locally at: /Users/username/.hyperdash/logs/print-example/print-example_2017-09-16t23-00-25-833357.log
```

Scikit-Learn example:
```
from sklearn import datasets
from sklearn import svm
from sklearn.metrics import accuracy_score
from hyperdash import Experiment

exp = Experiment("Digits classifier")

# Record the value of gamma for this experiment
gamma = exp.param("gamma",0.001)

clf = svm.SVC(gamma=gamma)
digits = datasets.load_digits()

test_cases = exp.param("Test cases", 50)
X_train, y_train = digits.data[:-test_cases], digits.target[:-test_cases]
X_test, y_test = digits.data[-test_cases:], digits.target[-test_cases:]

exp.param("Training cases", len(X_train))

clf.fit(X_train, y_train)

exp.metric("accuracy", accuracy_score(X_test, y_test))

exp.end()
```


## Installation

`pip install --upgrade pip && pip install hyperdash`

## Usage

The Hyperdash SDK requires a valid API key in order to function. Luckily, the `hyperdash login` (if you already have an account) and `hyperdash signup` (if you don't) commands will automatically install one for you.

If you'd rather manage your API key manually, then review the "API Key Storage" section below.

### Standalone Script
The easiest way to use the Hyperdash SDK is to simply prefix any terminal command with `hyperdash run`:

```
hyperdash run -n "My test python script" python my_test_script.py
```

or

```
hyperdash run -n "My test bash script" ./my_test_bash_script.sh
```

It doesn't matter what language your script is written in, if it can be executed from the command line then you can wrap it with the `run`  command

### Decorating a Python function
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

Once you've imported our library, run your program as you normally would:

`python test_script.py`

That's it! Open the Hyperdash mobile app and you should see your logs start to stream in!

### IPython/Jupyter Notebook

Hyperdash works in IPython/Jupyter notebooks as well. In fact, you can use the exact same code from the previous section in a Jupyter notebook and it will work just fine.

However, if you'd rather have Hyperdash monitor the execution of a specific Jupyter cell, as opposed to a decorated function, you can use our custom IPython magic. Example:

```
Cell 1
 ___________________________________________________________
|  from hyperdash import monitor_cell                       |
|___________________________________________________________|

Cell 2
 ___________________________________________________________
|  %%monitor_cell dogs vs. cats                            |
|  print("Epoch 1, accuracy: 50%")                          |
|  time.sleep(2)                                            |
|  print("Epoch 2, accuracy: 75%")                          |
|  time.sleep(2)                                            |
|  print("Epoch 3, accuracy: 100%")                         |
|__________________________________________________________ |
```

Note that importing the cell magic and invoking it must occur in two different cells.

### API key storage

If you signed up through the CLI, then your API key is already installed in hyperdash.json file in the home directory of your user.

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
