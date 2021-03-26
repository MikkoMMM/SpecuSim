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
        return generator.generate(
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
        return ""


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
        # Possibly allow True if same object?
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
        self.talking_speed = 5+0.1  # How long (in characters per second) the speech bubble should stay visible
        self.lock = threading.Lock()  # Just in case
        self.min_time = datetime(1, 1, 1, 1, 1, 1, 342380)
        self.max_time = datetime(9999, 12, 1, 1, 1, 1, 342380)
        for _ in range(4):
            thread.start_new_thread(self.thread_loop, args=())


    def thread_loop(self):
        while True:
            speech_task = self.queue.get(block=True)
            speech_task.speaker.speech_field.show()
            talking_started = datetime.now()
            context = "You are speaking to a person."
            action = f"You say: \"{speech_task.text.strip()}\"\nThey answer: \""

            result=act(self.generator, context, action,
                output=speech_task.speaker.speech_field, debug=self.debug)
            on_screen_time = max(30/self.talking_speed, len(result)/self.talking_speed)
            taskMgr.doMethodLater(max(0.1, on_screen_time-0.1), speech_task.speaker.speech_field.hide, 'HSB', extraArgs=[])

            with self.lock:
                speech_task.speaker.can_talk_time = talking_started + timedelta(seconds=on_screen_time)


    def new_speech_task(self, speaker, text):
        if not text:  # Nothing to react to
            return
        with self.lock:
            task = SpeechTask(self.min_time, speaker, text)
            if datetime.now() >= speaker.can_talk_time:
                self.queue.put(task)
                speaker.can_talk_time = self.max_time
            else:
                self.wait_queue.append(task)


    def update(self):
        """Bookkeeping that needs to be done every frame
        """
        i = 0
        with self.lock:
            while i < len(self.wait_queue):
                if datetime.now() >= self.wait_queue[i].speaker.can_talk_time:
                    speech_task = self.wait_queue.pop(i)
                    speech_task.priority = speech_task.speaker.can_talk_time
                    self.queue.put(speech_task)
                    speech_task.speaker.can_talk_time = self.max_time
                else:
                    i += 1
