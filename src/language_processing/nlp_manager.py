# Credit: AI Dungeon 2: Clover Edition

from src.getconfig import settings
from os import _exit
import traceback
from queue import PriorityQueue
from direct.stdpy import thread, threading
from time import sleep
from datetime import datetime, timedelta


def act(generator, context, action, output=None, debug=True):
    temperature = settings.getfloat('temp')
    repetition_penalty = settings.getfloat('rep-pen')
    try:

        if not context.strip() + action.strip():
            return None
        return generator.generate(
            action,
            context,
            temperature=temperature,
            repetition_penalty=repetition_penalty, output=output)

    except Exception as e:
        print()
        print("Natural language processing has crashed!")
        print("Context: " + context)
        print("Action: " + action)
        print("Temperature: " + str(temperature))
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
    lock = threading.Lock()  # Just in case
    talking_speed = 5  # How long (in characters per second) the speech bubble should stay visible


    def __init__(self, generator, debug=False):
        self.queue = PriorityQueue()
        self.wait_queue = []
        self.debug = debug
        self.generator = generator
        for _ in range(4):
            thread.start_new_thread(self.thread_loop, args=())


    def thread_loop(self):
        while True:
            speech_task = self.queue.get(block=True)
            speech_task.speaker.speech_field.show()
            # talking_started = datetime.now()
            context = "You are speaking to a person."
            action = f"You say: \"{speech_task.text.strip()}\"\nThey answer: \""

            result=act(self.generator, context, action,
                output=speech_task.speaker.speech_field, debug=self.debug)
            on_screen_time = max(30.0/self.talking_speed, len(result)/self.talking_speed)
            with self.lock:
                speech_task.speaker.speech_field.hide_task = taskMgr.doMethodLater(on_screen_time, speech_task.speaker.hide_speech_field,
                                                                               'HSB', extraArgs=[])
                speech_task.speaker.can_talk_more = True


    def new_speech_task(self, speaker, text):
        if not text:  # Nothing to react to
            return
        with self.lock:
            task = SpeechTask(datetime.now(), speaker, text)
            if speaker.speech_field.hide_task:
                taskMgr.remove(speaker.speech_field.hide_task)
            if speaker.can_talk_more:
                self.queue.put(task)
                speaker.can_talk_more = False
            else:
                self.wait_queue.append(task)


    def update(self):
        """Bookkeeping that needs to be done every frame
        """
        i = 0
        with self.lock:
            while i < len(self.wait_queue):
                if self.wait_queue[i].speaker.can_talk_more:
                    speech_task = self.wait_queue.pop(i)
                    speech_task.priority = datetime.now()
                    self.queue.put(speech_task)
                    speech_task.speaker.can_talk_more = False
                else:
                    i += 1
