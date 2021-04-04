import gc
import os
import random
import struct
from math import sqrt, radians
from pathlib import Path
from time import sleep

import torch
from direct.gui.DirectGui import DirectFrame, DirectEntry
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.InputStateGlobal import inputState
from direct.showbase.ShowBase import ShowBase
from direct.stdpy import thread, threading
from direct.task import Task
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletWorld
from panda3d.bullet import ZUp
from panda3d.bullet import get_bullet_version
from panda3d.core import BitMask32
from panda3d.core import PNMImage, Filename
from panda3d.core import SamplerState, TextNode
from panda3d.core import Vec3, load_prc_file_data, PStatClient, CullBinManager

from src.camera import CameraControl
from src.getconfig import settings, logger
from src.humanoid import Humanoid
from src.language_processing.gpt2generator import GPT2Generator
from src.language_processing.nlp_manager import NLPManager
from src.menu import Menu
from src.utils import create_or_load_walk_map, create_shader_terrain_mesh
from multiprocessing.pool import ThreadPool


def load_language_model(notice_text_obj, menu_img, return_value):
    model_dir = "language_models"
    models = [x for x in Path(model_dir).iterdir() if x.is_dir()]
    failed_env_load = False
    while True:
        try:
            transformers_pretrained = os.environ.get("TRANSFORMERS_PRETRAINED_MODEL", False)
            if transformers_pretrained and not failed_env_load:
                # Keep it as a string, so that transformers library will load the generic model
                model = transformers_pretrained
                assert isinstance(model, str)
            else:
                # Convert to path, so that transformers library will load the model from our folder
                if not models:
                    raise FileNotFoundError(
                        'There are no models in the models directory! You must download a pytorch compatible model!')
                if os.environ.get("MODEL_FOLDER", False) and not failed_env_load:
                    model = Path(model_dir + os.environ.get("MODEL_FOLDER", False))
                elif len(models) > 1:
                    notice_text_obj.text = "You have multiple models in your models folder. Please select one to load:"

                    menu = Menu(menu_img, aspect_ratio_keeping_scale=1, hide_afterwards=True)
                    menu.change_button_style(PNMImage(Filename("textures/empty_button_52.png")), aspect_ratio_keeping_scale=2)
                    menu.change_select_style(PNMImage(Filename("textures/select.png")), aspect_ratio_keeping_scale=2)

                    for i in range(len(models)):
                        menu.add_button(models[i].name, _nlp_model_chosen, args=[models[i], notice_text_obj, return_value], y=-0.1 + 0.1 * i)
                    menu.add_button("(Exit)", exit, y=0.5)
                    menu.show_menu()
                    return
                else:
                    model = models[0]
                    print("Using model: " + str(model))
                assert isinstance(model, Path)
            _nlp_model_chosen(model, notice_text_obj, return_value)
            break
        except OSError:
            if len(models) == 0:
                notice_text_obj.text = "fYou do not seem to have any models installed. Place a model in the '{model_dir}' " \
                                            "subfolder"
                base.graphicsEngine.render_frame()
                # Scan for models again
                models = [x for x in Path(model_dir).iterdir() if x.is_dir()]
            else:
                failed_env_load = True
                notice_text_obj.text = "Model could not be loaded. Please try another model."
            continue
        except KeyboardInterrupt:
            print("Model load cancelled. ")
            exit(0)


def _nlp_model_chosen(model, notice_text_obj, return_value):
    notice_text_obj.text = "Loading language model. This may take a few minutes."

    assert isinstance(model, Path)
    load_nlp_task = threading.Thread(target=_load_generator, kwargs={
        "return_value": return_value,
        "model_path": model,
        "generate_num": settings.getint("generate-num"),
        "temperature": settings.getfloat("temp"),
        "repetition_penalty": settings.getfloat("rep-pen")})
    load_nlp_task.start()

    while load_nlp_task.is_alive():
        base.graphicsEngine.render_frame()
        sleep(0.05)

    # May be needed to avoid out of mem
    gc.collect()
    torch.cuda.empty_cache()


def _load_generator(return_value="", **kwargs):
    return_value.append(GPT2Generator(**kwargs))
