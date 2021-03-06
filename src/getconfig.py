import configparser
import logging

config = configparser.ConfigParser()
config.read("config.ini")
settings = config["Settings"]
debug = config["Debug"]

logger = logging.getLogger(__name__)
logLevel = debug.getint("log-level")
oneLevelUp = 20

# I don't know if this will work before loading the transformers module?
# silence transformers outputs when loading model
logging.getLogger("transformers.tokenization_utils").setLevel(logLevel + oneLevelUp)
logging.getLogger("transformers.modeling_utils").setLevel(logLevel + oneLevelUp)
logging.getLogger("transformers.configuration_utils").setLevel(logLevel + oneLevelUp)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logLevel + oneLevelUp,
)
logger.setLevel(logLevel)

"""
Settings descriptions and their default values keyed by their name.
"""
setting_info = {
    "temp":             ["Higher values make the AI more random.", 0.4],
    "rep-pen":          ["Controls how repetitive the AI is allowed to be.", 1.2],
    "force-cpu":        ["Whether to force CPU instead of GPU usage in language processing", 0],
    "generate-num":     ["Approximate number of words to generate.", 60],
    "enable-fps-meter": ["Show a frames per second counter", 1],
}

debug_info = {
    "log-level":        ["Development log level. <30 is for developers.", 30],
    "enable-pstats":    ["Enable PStats performance analysis support", 0],
    "debug-joints":     ["Visually debug joints", 0],
    "nlp-debug":        ["Stuff that makes debugging natural language processing faster", 0],
}
