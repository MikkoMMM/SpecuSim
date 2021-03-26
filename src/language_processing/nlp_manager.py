# Credit: AI Dungeon 2: Clover Edition

from src.language_processing.getconfig import settings
from os import _exit
import traceback
from queue import PriorityQueue
from direct.stdpy import thread, threading
from time import sleep
from datetime import datetime, timedelta


def act(generator, context, action, output=None, debug=True):
    if debug:
        print("Context: " + context)
        print("Action: " + action)
        print()
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
    def __init__(self, generator, debug=False):
        self.queue = PriorityQueue()
        self.wait_queue = []
        self.debug = debug
        self.generator = generator
        self.lock = threading.Lock()  # Just in case
        for _ in range(4):
            thread.start_new_thread(self.thread_loop, args=())


    def thread_loop(self):
        while True:
            if not self.queue.empty():
                with self.lock:
                    speech_task = self.queue.get()
                talking_started = datetime.now()

                act(self.generator, "You are speaking to a person.", "You say to him: " + speech_task.text,
                    output=speech_task.speaker.speech_field, debug=self.debug)

                with self.lock:
                    speech_task.speaker.can_talk_time = talking_started + timedelta(seconds=10)

            sleep(0.05)


    def new_speech_task(self, speaker, text):
        with self.lock:
            task = SpeechTask(0, speaker, text)
            if datetime.now() >= speaker.can_talk_time:
                self.queue.put(task)
                speaker.can_talk_time = datetime(9999, 12, 1, 1, 1, 1, 342380)
            else:
                self.wait_queue.append(task)


    def update(self):
        """Bookkeeping that needs to be done every frame
        """
        with self.lock:
            for i in range(len(self.wait_queue)):
                if datetime.now() >= self.wait_queue[i].speaker.can_talk_time:
                    speech_task = self.wait_queue.pop(i)
                    speech_task.priority = speech_task.speaker.can_talk_time
                    self.queue.put(speech_task)
