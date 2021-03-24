# Credit: AI Dungeon 2: Clover Edition

from src.language_processing.getconfig import settings
from src.language_processing.utils import format_result, format_input


def act(generator, context, action, format=True, output=None):
    if not context.strip() + action.strip():
        return None
    assert (settings.getint('top-keks') is not None)
    result = generator.generate(
        action,
        context,
        temperature=settings.getfloat('temp'),
        top_p=settings.getfloat('top-p'),
        top_k=settings.getint('top-keks'),
        repetition_penalty=settings.getfloat('rep-pen'), output=output)
    return format_result(result) if format else result
