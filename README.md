# Hyperdash Python SDK
[![CircleCI](https://circleci.com/gh/hyperdashio/hyperdash-sdk-py/tree/master.svg?style=svg)](https://circleci.com/gh/hyperdashio/hyperdash-sdk-py/tree/master)

[Hyperdash](https://hyperdash.io) is a machine learning monitoring library capable of running alongside Tensorflow, Scikit-Learn, and other modeling libraries. It was developed with a focus on enabling fast knowledge gain.

Use Hyperdash if you're looking for cloud-based model monitoring that:

* Is fast and easy-to-use with scripts and Jupyter.
* Tracks your hyperparameters across different model experiments.
* Graphs performance metrics (loss, reward, etc.) in real-time.
* Can be viewed remotely on [__web__](https://hyperdash.io/dashboard), [__iOS__](https://itunes.apple.com/us/app/hyperdash-machine-learning-monitoring/id1257582233), and [__Android__](https://play.google.com/store/apps/details?id=com.hyperdash) without self-hosting (e.g. Tensorboard).
* Saves your experiment's print output (standard out / error) as a local log file.
* Notifies you when a long-running experiment has finished.

Hyperdash is compatible with: **Python 2.7-3.6**

## Installation
*Foreword: We care deeply about making Hyperdash fast and easy to install  on Linux, Mac, and Windows. If you find a snag along the way, please let us know at support@hyperdash.io!*

Install Hyperdash in terminal from [pip](https://packaging.python.org/tutorials/installing-packages/#requirements-for-installing-packages). Installing within a python virtual environment such as [virtualenv](https://github.com/pypa/virtualenv) is recommended. If you are having trouble installing via pip, a virtual environment will usually fix the problem.
```bash
$ pip install --upgrade pip && pip install hyperdash
```
By installing via pip, you can call hyperdash from the command line via both `hyperdash` and `hd`.
```bash
# Login if you have an account
$ hyperdash login

# Or signup free with an email
$ hd signup
```
After `login` or `signup`, an API key is saved to your local machine for automatic authorization. If you'd rather manage your API key manually, then review the "API Key Storage" section below.

You're ready to use Hyperdash! Make sure Hyperdash works by running:
```
$ hd demo
```

# Learn Hyperdash in 60 seconds
## Pure logging 
If all you need is logging and notifications, simply prefix **any** terminal command:
```bash
hd run -n "Hotdog CNN" python hotdog.py
```
Or use pipe:
```bash
./catsdogs.sh | hd pipe
```
In Jupyter:

<img width="300" alt="screen shot 2017-09-24 at 7 27 37 pm" src="https://user-images.githubusercontent.com/1892071/30790069-835da34c-a15e-11e7-954f-9b90ca5634f0.png">


## Experiment instrumentation
If you are interested in tracking **hyperparameters** and **performance metrics**, you'll want to use the **Experiment** api. Experiment objects are created with a model name, then auto-started and auto-incremented. By default, Experiment will record print logs. Here is an example of a simple Scikit Learn classifier instrumented:
```python
# digits.py
from sklearn import svm, datasets
from hyperdash import Experiment

# Preprocess data
digits = datasets.load_digits()
test_cases = 50
X_train, y_train = digits.data[:-test_cases], digits.target[:-test_cases]
X_test, y_test = digits.data[-test_cases:], digits.target[-test_cases:]

# Create an experiment with a model name, then autostart
exp = Experiment("Digits Classifier")
# Record the value of hyperparameter gamma for this experiment
gamma = exp.param("gamma", 0.1)
# Param can record any basic type (Number, Boolean, String)

classifer = svm.SVC(gamma=gamma)
classifer.fit(X_train, y_train)

# Record a numerical performance metric
exp.metric("accuracy", classifer.score(X_test, y_test))

# Cleanup and mark that the experiment successfully completed
exp.end()
```
Hyperparameters and metrics are pretty printed for your logs and reference:
```
{ gamma     : 0.001 }
| accuracy  : 1.000 |
Experiment "digits-classifier_2017-09-20t18-50-55-258215" complete.
Logs are available locally at: /Users/username/.hyperdash/logs/digits-classifier/digits-classifier_2017-09-20t18-50-55-258215.log
```
You can also disable logging by setting `capture_io` to false:
```python
exp = Experiment("Digits Classifier", capture_io=False)
```
## You've learned Hyperdash!
Visualize your experiments in the Hyperdash [__web__](https://hyperdash.io/dashboard), [__iOS__](https://itunes.apple.com/us/app/hyperdash-machine-learning-monitoring/id1257582233), and [__Android__](https://play.google.com/store/apps/details?id=com.hyperdash) apps.
________________

# More information
- Jupyter/IPython tips
- Decorator Experiment API
- API key management

## IPython/Jupyter Notebook

<img width="700" alt="Hyperdash in Jupyter" src="https://user-images.githubusercontent.com/1892071/30736813-1a7fcb7e-9f39-11e7-812b-f1b77ee33dab.png">
 
Note: by default all print statements will be redirected to the cell that creates the experiment object due to capturing Jupyter's stdio. Use `exp = Experiment("model name", capture_io=False)` for normal printing, but no logging.

The SDK currently doesn't support mid-experiment parameter redeclaration. Remember to `end()` your experiment before redeclaring `exp`.

## Decorator experiment API
If your experiment is wrapped in a function, the decorator API saves you the trouble of having to remember to write `exp.end()`. The exact argument `exp` must be passed into the wrapped function to get access to the Experiment object.
```python
from hyperdash import monitor

@monitor("dogs vs. cats")
def train_dogs_vs_cats(exp): # Get Experiment object as argument to function.
  lr = exp.param("learning rate", 0.005)
  model = Model(lr)
  model.fit()
  exp.metric(model.accuracy())
```
## API Keys
### Storage

If you signed up through the CLI, then your API key is already installed in hyperdash.json file in the home directory of your user.

You can alternatively override this API key with a hyperdash.json file in your local directory (so you can have different API keys for different projects) or with the HYPERDASH_API_KEY environment variable.

Finally, the monitor function accepts an api_key_getter argument that if passed in will be called everytime we need to retrieve your API key. Example:

```python
# test_script.py

from hyperdash import monitor

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
