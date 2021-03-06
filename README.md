# What is SpecuSim: The World Simulator?
SpecuSim: The World Simulator is a gambit. It's a platform for games, and it will either fail and fall into obscurity, or earn a place in video game history as an inspiration for successful other game titles (while not necessarily ever being by itself very well known even still). The gambit is this: find ways to produce lots of meaningful content with relatively minor human effort. Compare it to Dwarf Fortress; something that pushes the envelope regarding what's deemed possible in indie game development while commercialization never being a huge priority.

Even still it's going to take many, many years before there's much of anything worth playing. A complex simulated world that this platform for games is mostly useful for doesn't come easily. In fact, it's impossible for a lot of current systems to run the full game with playable performance, because the technologies used are chosen according to not what gives decent results today, but on the basis of "what might be" in the future. And to be even clearer of the intention of being a useful inspiration or even a basis for other projects, SpecuSim is permissively licensed.

The main game mode of SpecuSim is a sandbox RPG. The main game mode and the platform (which is itself an extention to the Panda3D game engine) are developed in a close symbiosis, and hence the game mode can also be referred to as "SpecuSim".

# Minimal installation
With this installation you are limited to game modes that don't use natural language processing.

## Requirements
### Hardware
* 1 GB Graphics Memory
* OpenGL 3.2 capable GPU (and drivers)

#### Motion controller
Currently these options are supported:

Nothing. All support is currently on halt. But you should have a mouse instead.


### Software
* Python 3.6 or later

## Installation
Install the required Python modules:
```
pip3 install -r requirements_minimal.txt
```

## Starting the game
To play, go to the root directory of SpecuSim and run:
```
python3 specusim.py
```


# Full installation

## Requirements
### Hardware
* 5 GB Graphics Memory
* The GPU should preferably be NVIDIA's, but AMD may work with the ROCm version of PyTorch, too (no guarantees).
* OpenGL 3.2 capable GPU (and drivers)

#### Motion controller
Currently these options are supported:

Nothing. All support is currently on halt. But you should have a mouse instead.


### Software
* Python 3.6 or later
* CUDA enabled graphics driver


## Installation
First, you need to install the required Python modules:
```
pip3 install -r requirements_all.txt
```

### AI models
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
python3 specusim.py
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
