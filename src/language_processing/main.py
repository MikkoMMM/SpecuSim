def get_generator():
    models = [x for x in Path('language_models').iterdir() if x.is_dir()]
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
                    model = Path("models/" + os.environ.get("MODEL_FOLDER", False))
                elif len(models) > 1:
                    output("You have multiple models in your models folder. Please select one to load:", 'message')
                    list_items([m.name for m in models] + ["(Exit)"], "menu")
                    model_selection = input_number(len(models))
                    if model_selection == len(models):
                        output("Exiting. ", "message")
                        exit(0)
                    else:
                        model = models[model_selection]
                else:
                    model = models[0]
                    logger.info("Using model: " + str(model))
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
                output("You do not seem to have any models installed.", "error")
                output("Place a model in the 'models' subfolder and press enter", "error")
                input("")
                # Scan for models again
                models = [x for x in Path('models').iterdir() if x.is_dir()]
            else:
                failed_env_load = True
                output("Model could not be loaded. Please try another model. ", "error")
            continue
        except KeyboardInterrupt:
            output("Model load cancelled. ", "error")
            exit(0)
    return generator
