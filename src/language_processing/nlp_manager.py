# Credit: AI Dungeon 2: Clover Edition

from src.language_processing.getconfig import settings
from os import _exit
import traceback
from queue import PriorityQueue
from direct.stdpy import thread
from time import sleep


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


class SpeechTask:
    def __init__(self, priority, speaker, text):
        self.priority = priority
        self.speaker = speaker
        self.text = text

    def __lt__(self, obj):
        return self.priority < obj.priority

    def __le__(self, obj):
        return self.priority <= obj.priority

    def __eq__(self, obj):
        return False

    def __ne__(self, obj):
        return True

    def __gt__(self, obj):
        return self.priority > obj.priority

    def __ge__(self, obj):
        return self.priority >= obj.priority


class NLPManager:
    def __init__(self):
        self.queue = PriorityQueue()
        thread.start_new_thread(self.thread_loop, args=())
#        thread.start_new_thread(target=nlp_manager.act, args=(self.generator, "You are speaking to a man.", "You say to him: \"Hello!\""),
        #        kwargs={
#            "output": self.npc1.speech_field, "debug": self.nlp_debug})

    def thread_loop(self):
        while True:
            if not self.queue.empty():
                speech_task = self.queue.get()
                speech_task.speaker.say(speech_task.text)

            sleep(0.1)

    def new_speech_task(self, speaker, text):
        self.queue.put(SpeechTask(0, speaker, text))
