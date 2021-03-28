import configparser
import logging

config = configparser.ConfigParser()
config.read("config.ini")
settings = config["Settings"]

logger = logging.getLogger(__name__)
logLevel = settings.getint("log-level")
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
These settings, their descriptions, and their defaults appear in the settings menu and the /help prompt.
"""
setting_info = {
    "temp":             ["Higher values make the AI more random.", 0.4],
    "rep-pen":          ["Controls how repetitive the AI is allowed to be.", 1.2],
    "force-cpu":        ["Whether to force CPU instead of GPU usage in language processing", False],
    "generate-num":     ["Approximate number of words to generate.", 60],
    "log-level":        ["Development log level. <30 is for developers.", 30],
}
