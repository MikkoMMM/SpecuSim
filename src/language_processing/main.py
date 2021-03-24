# Credit: AI Dungeon 2: Clover Edition

from src.language_processing.getconfig import settings
from os import _exit
import traceback


def act(generator, context, action, output=None, debug=True):
    temperature = settings.getfloat('temp')
    top_p = settings.getfloat('top-p')
    top_k = settings.getint('top-keks')
    repetition_penalty = settings.getfloat('rep-pen')
    try:

        if not context.strip() + action.strip():
            return None
        assert (settings.getint('top-keks') is not None)
        result = generator.generate(
            action,
            context,
            temperature=settings.getfloat('temp'),
            top_p=settings.getfloat('top-p'),
            top_k=settings.getint('top-keks'),
            repetition_penalty=settings.getfloat('rep-pen'), output=output, debug=debug)
    except Exception as e:
        print()
        print("Natural language processing has crashed!")
        print("Context: " + context)
        print("Action: " + action)
        print("Temperature: " + str(temperature))
        print("top_p: " + str(top_p))
        print("top_k: " + str(top_k))
        print("Repetition penalty: " + str(repetition_penalty))
        print()
        traceback.print_exc()
        print(e)

        if debug:
            # Probably a bad idea, but for now hastens the debugging process
            _exit(1)
