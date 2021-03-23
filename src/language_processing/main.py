# Credit: AI Dungeon 2: Clover Edition

from pathlib import Path
import os
from src.language_processing.gpt2generator import GPT2Generator
from src.language_processing.getconfig import config, setting_info, settings
from src.menu import Menu
from panda3d.core import PNMImage, Filename


def get_generator(text_node, menu_img):
    model_dir = "language_models"
    models = [x for x in Path(model_dir).iterdir() if x.is_dir()]
    generator = None
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
                    text_node.text = "You have multiple models in your models folder. Please select one to load:"

                    menu = Menu(menu_img, aspect_ratio_keeping_scale=1, auto_hide=True)
                    menu.change_button_style(PNMImage(Filename("textures/empty_button_52.png")), aspect_ratio_keeping_scale=2)
                    menu.change_select_style(PNMImage(Filename("textures/select.png")), aspect_ratio_keeping_scale=2)

                    for i in range (len( models)):
                        menu.add_button(models[i].name, exit, args=[models[i]], y=-0.1+0.1*i)
                    menu.add_button("(Exit)", exit, y=0.5)
                    menu.show_menu()
                    return None
                else:
                    model = models[0]
                    print("Using model: " + str(model))
                assert isinstance(model, Path)
            generator = GPT2Generator(
                model_path=model,
                generate_num=settings.getint("generate-num"),
                temperature=settings.getfloat("temp"),
                top_k=settings.getint("top-keks"),
                top_p=settings.getfloat("top-p"),
                repetition_penalty=settings.getfloat("rep-pen"),
            )
            break
        except OSError:
            if len(models) == 0:
                text_node.text = "You do not seem to have any models installed. Place a model in the '"+model_dir+"' subfolder"
                base.graphicsEngine.render_frame()
                # Scan for models again
                models = [x for x in Path(model_dir).iterdir() if x.is_dir()]
            else:
                failed_env_load = True
                text_node.text = "Model could not be loaded. Please try another model."
            continue
        except KeyboardInterrupt:
            print("Model load cancelled. ")
            exit(0)
    return generator
