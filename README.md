# Requirements
## Hardware
* 5 GB Graphics Memory (or 1 GB if not using natural language processing)
* The GPU should preferably be NVIDIA's, but AMD may work with the ROCm version of PyTorch, too (no guarantees).
* OpenGL 4.3 capable GPU (and drivers)

### Motion controller
Currently these options are supported:

Nothing. All support is currently on halt. But you should have a mouse instead.


## Software
* Python 3.6 or later
* CUDA enabled graphics driver


# Installation
First, you need to install the required Python modules:
pip install -r requirements.txt 

## AI models
You'll also need an AI model to use the natural language processing features. It's to be placed in the language_models directory. The PyTorch version of the original AID2 model is being distributed by bittorrent:

[Torrent File](model.torrent) 

[Magnet Link](magnet:?xt=urn:btih:17dcfe3d12849db04a3f64070489e6ff5fc6f63f&dn=model_v5_pytorch&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce&tr=udp%3a%2f%2fopen.stealth.si%3a80%2fannounce&tr=udp%3a%2f%2fp4p.arenabg.com%3a1337%2fannounce&tr=udp%3a%2f%2ftracker.coppersurfer.tk%3a6969%2fannounce&tr=udp%3a%2f%2ftracker.cyberia.is%3a6969%2fannounce&tr=udp%3a%2f%2ftracker.moeking.me%3a6969%2fannounce&tr=udp%3a%2f%2f9.rarbg.me%3a2710%2fannounce&tr=udp%3a%2f%2ftracker3.itzmx.com%3a6961%2fannounce)

```
magnet:?xt=urn:btih:17dcfe3d12849db04a3f64070489e6ff5fc6f63f&dn=model_v5_pytorch&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce&tr=udp%3a%2f%2fopen.stealth.si%3a80%2fannounce&tr=udp%3a%2f%2fp4p.arenabg.com%3a1337%2fannounce&tr=udp%3a%2f%2ftracker.coppersurfer.tk%3a6969%2fannounce&tr=udp%3a%2f%2ftracker.cyberia.is%3a6969%2fannounce&tr=udp%3a%2f%2ftracker.moeking.me%3a6969%2fannounce&tr=udp%3a%2f%2f9.rarbg.me%3a2710%2fannounce&tr=udp%3a%2f%2ftracker3.itzmx.com%3a6961%2fannounce
```

Once downloaded your language_models folder should look like this:
```
    ./language_models
    └── <MODEL-NAME>
        ├── config.json
        ├── merges.txt
        ├── pytorch_model.bin
        └── vocab.json
```

## Starting the game
To play, go to the root directory of SpecuSim and run:
```
python specusim.py
```

# Contributing
We do accept contributions, but there's currently very little English guidance on the project's goals. So probably talk first before trying to submit major changes.

All changes must be compatible with the MIT License. Refer to [here](https://github.com/MikkoMMM/SpecuSim/blob/main/.github/pull_request_template.md) for further details.


## Style guide
These are general guidelines for the code style conventions in this project. Use some common sense regarding how strictly to adhere to these.

Docstrings should use the Google Style.
https://gist.github.com/redlotus/3bc387c2591e3e908c9b63b97b11d24e

For other matters, if you are used to the PEP8 style, use that.

Some basics are:

A level of indentation uses 4 spaces.

Naming conventions are:

* .py file names should be short and all-lowercase
* joined_lower for functions, methods, attributes and variables
* ALL_CAPS for constants
* CapWords for classes
