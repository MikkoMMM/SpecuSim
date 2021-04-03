"""Natural language processing with GPT2-like Pytorch models

With this module, you can give a start input to generate(), and it will continue that prompt.
The module was heavily streamlined from Clover Edition. Some experimental features were removed in the process, too.
"""

from pathlib import Path
from typing import Union

import torch
import torch.nn.functional as F
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from src.getconfig import settings, logger
from .utils import format_result

if not settings.getboolean('force-cpu') and not torch.cuda.is_available():
    logger.warning('CUDA is not available, you are limited to CPU only.')

DTYPE = torch.float32 if ((not torch.cuda.is_available()) or settings.getboolean('force-cpu')) else torch.float16
logger.info('Cuda Available: {}    Force CPU: {}    Precision: {}'.format(torch.cuda.is_available(),
                                                                          settings.getboolean('force-cpu'),
                                                                          '32-bit' if DTYPE == torch.float32 else '16-bit'))

# warnings.filterwarnings("ignore")
MODEL_CLASSES = {
    "gpt2": (GPT2LMHeadModel, GPT2Tokenizer),
    # "gpt2-experimental": (GPT2LMHeadModelExperimental, GPT2Tokenizer),
}


# the tokenizer does not preserve white space at the front of the string.
# so we will append something else to the front of the string and then remove it after tokenization
def encode_prepend_newline(tokenizer, s):
    return tokenizer.encode('====\n\n' + s)[2:]


def top_k_top_p_filtering(logits, top_k=0, top_p=0.0, filter_value=-float("Inf")):
    """ Filter a distribution of logits using top-k and/or nucleus (top-p) filtering
        Args:
            logits: logits distribution shape (batch size x vocabulary size)
            top_k > 0: keep only top k tokens with highest probability (top-k filtering).
            top_p > 0.0: keep the top tokens with cumulative probability >= top_p (nucleus filtering).
                Nucleus filtering is described in Holtzman et al. (http://arxiv.org/abs/1904.09751)
        From: https://gist.github.com/thomwolf/1a5a29f6962089e871b94cbd09daf317
    """
    top_k = min(top_k, logits.size(-1))  # Safety check
    if top_k > 0:
        # Remove all tokens with a probability less than the last token of the top-k
        indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
        logits[indices_to_remove] = filter_value

    if top_p > 0.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

        # Remove tokens with cumulative probability above the threshold
        sorted_indices_to_remove = cumulative_probs > top_p
        # Shift the indices to the right to keep also the first token above the threshold
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0

        # scatter sorted tensors to original indexing
        indices_to_remove = sorted_indices_to_remove.scatter(
            dim=-1, index=sorted_indices, src=sorted_indices_to_remove
        )
        logits[indices_to_remove] = filter_value
    return logits


# length should be max length, other settings should be removed, device should not be set
# we could possibly optimize this by having larger batch sizes but it would likely double or more the memory requirements
def sample_sequence(
        model, length, context, temperature=1, top_k=0, top_p=0.8, repetition_penalty=1.0, device="cpu",
        disallowed_starts=('\"',), stop_chars_included=(), stop_chars_not_included=('\"', "\n"),
        stop_tokens=None, tokenizer=None, output=None,
):
    """Actually generate the tokens"""
    logger.debug(f'temp: {temperature}    generate_num: {length}    rep-pen: {repetition_penalty}')
    context_tokens = context
    context = torch.tensor(context, dtype=torch.long, device=device)
    generated = context
    next_token = context
    pasts = None
    formatted_text = ""
    disallowed_start_len = len(max(disallowed_starts, default=""))
    with torch.no_grad():
        for j in range(length):
            input_ids_next = next_token

            # Note: we could also use 'past' with GPT-2/Transfo-XL/XLNet/CTRL (cached hidden-states)
            logits, pasts = model(input_ids=input_ids_next, past=pasts)
            logits = logits[-1, :].float()

            # Originally the order was Temperature, Repetition Penalty, then top-k/p
            logits = top_k_top_p_filtering(logits, top_k=top_k, top_p=top_p)

            logits = logits / (temperature if temperature > 0 else 1.0)

            # repetition penalty from CTRL (https://arxiv.org/abs/1909.05858)
            for k in set(generated.tolist()):
                logits[k] /= repetition_penalty

            if temperature == 0:  # greedy sampling:
                next_token = torch.argmax(logits, dim=-1).unsqueeze(-1)
            else:
                next_token = torch.multinomial(
                    F.softmax(logits, dim=-1), num_samples=1
                )
            generated = torch.cat((generated, next_token), dim=-1)
            # Decode into plain text
            o = generated[len(context_tokens):].tolist()
            generated.text = tokenizer.decode(
                o, clean_up_tokenization_spaces=False, skip_special_tokens=True
            )

            # Check whether stop characters were in there
            last_token = tokenizer.decode(o[-1], clean_up_tokenization_spaces=False, skip_special_tokens=True)

            if len(generated.text) - len(last_token) <= disallowed_start_len:
                for ele in disallowed_starts:
                    if result_replace(generated.text).startswith(ele):
                        return ""

            for ele in stop_chars_not_included:
                place = last_token.find(ele)
                if place >= 0:
                    formatted_text = format_result(result_replace(formatted_text + last_token[:place]))
                    if output is not None:
                        output.set_text(formatted_text)
                    logger.debug("Generated result is: `%r`", generated.text)
                    return formatted_text

            for ele in stop_chars_included:
                place = last_token.find(ele)
                if place >= 0:
                    formatted_text = format_result(result_replace(formatted_text + last_token[:place + len(ele)]))
                    if output is not None:
                        output.set_text(formatted_text)
                    logger.debug("Generated result is: `%r`", generated.text)
                    return formatted_text

            formatted_text = format_result(result_replace(generated.text))
            if output is not None:
                output.set_text(formatted_text)

            if (
                    (stop_tokens is not None)
                    and (j > 4)
                    and (next_token[0] in stop_tokens)
            ):
                # Why the minimum tokens, j>X. Because sometimes the models starts with whitespace, which will strip away anyway.
                # Having a minimum amount of tokens before we stop usually means we don't just stop because of "\n " or similar
                logger.debug(
                    "Stopping generation as we found stop tokens. One of `%s`, in '%s'. token generated `%s`",
                    stop_tokens,
                    next_token,
                    j,
                )
                break
    logger.debug("Generated result is: `%r`", formatted_text)
    return formatted_text


def result_replace(result):
    # logger.debug("BEFORE RESULT_REPLACE: `%s`", repr(result))

    if len(result) == 0:
        return ""
    first_letter_capitalized = result[0].isupper()
    #        result = result.replace('."', '".')
    result = result.replace("#", "")
    result = result.replace("*", "")
    # TODO look at this I think blank lines should be fine or blacklisted at generation time
    result = result.replace("\n\n", "\n")

    if not first_letter_capitalized:
        result = result[0].lower() + result[1:]

    # this is annoying since we can already see the AIs output
    # logger.debug( "AFTER RESULT_REPLACE: `%r`. allow_action=%r", repr(result), allow_action)

    return result


class GPT2Generator:
    def __init__(
            self, generate_num=60, temperature=0.4, top_k=0, top_p=0.8, dtype=DTYPE,
            model_path: Union[str, Path] = Path('models', 'pytorch-gpt2-xl-aid2-v5'), repetition_penalty=1.2,
    ):
        self.generate_num = generate_num
        self.temp = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.dtype = dtype
        self.repetition_penalty = repetition_penalty
        self.max_history_tokens = 1024 - generate_num

        if isinstance(model_path, Path):
            self.checkpoint_path = model_path
            if not self.checkpoint_path.exists():
                raise FileNotFoundError(
                    "Could not find {} Make sure to download a pytorch model and put it in the models directory!".format(
                        str(self.checkpoint_path)))
        else:
            raise ValueError(f"model_path must be a Path, got {type(model_path)}")

        self.device = torch.device("cuda" if self.dtype == torch.float16 else "cpu")
        logger.info(
            "Using device={}, checkpoint={}, dtype={}".format(self.device, str(self.checkpoint_path), self.dtype))

        # Load tokenizer and model
        model_class, tokenizer_class = MODEL_CLASSES["gpt2"]
        self.tokenizer = tokenizer_class.from_pretrained(str(self.checkpoint_path))
        self.model = model_class.from_pretrained(str(self.checkpoint_path))
        self.model.to(self.dtype).to(self.device)
        self.model.eval()


    def generate(
            self, tokens, generate_num=None, temperature=None, top_k=None, top_p=None,
            repetition_penalty=None, stop_tokens=None, depth=0, output=None
    ):
        if stop_tokens is None:
            stop_tokens = self.tokenizer.encode(["<|endoftext|>", ">"])

        assert (temperature is not None)
        assert repetition_penalty

        logger.debug(
            "Text passing into model `%r`",
            self.tokenizer.decode(tokens),
        )
        generate_num = generate_num if (generate_num is not None) else self.generate_num
        temperature = temperature if (temperature is not None) else self.temp
        top_k = top_k if top_k is not None else self.top_k
        top_p = top_p if top_p is not None else self.top_p
        repetition_penalty = repetition_penalty if repetition_penalty is not None else self.repetition_penalty

        result = sample_sequence(
            model=self.model,
            context=tokens,
            length=generate_num,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            device=self.device,
            stop_tokens=stop_tokens,
            tokenizer=self.tokenizer,
            output=output,
        )

        if len(result) == 0:
            if depth < 20:
                logger.info("Model generated empty text trying again %r", depth)
                return self.generate(
                    context, prompt, temperature=temperature, top_p=top_p, top_k=top_k,
                    repetition_penalty=repetition_penalty, depth=depth + 1, output=output
                )
            else:
                logger.warn(
                    "Model generated empty text %r times. Try another action", depth
                )
        return result


    def memory_merge(self, *args):
        result = self._memory_merge(*args)
        assert (result)
        first, *rest = result
        # Finally remove the very first newline by doing some trickery
        return self.tokenizer.encode('====\n' + self.tokenizer.decode(first))[2:] + rest


    def _memory_merge(self, *args):
        merge_objects = [[]] * len(args)
        reversed_args = reversed(args)
        length = 0
        max_len = 0

        # Prioritize arguments that were plain strings, not lists
        for i, arg in enumerate(reversed_args, start=1):
            if isinstance(arg, str):
                new_tokens = encode_prepend_newline(self.tokenizer, arg)
                length += len(new_tokens)
                if length > self.max_history_tokens:
                    return sum(merge_objects, [])
                merge_objects[-i] = new_tokens
            else:
                max_len = max(len(arg), max_len)

        for i in range(1, max_len + 1):
            for j, arg in enumerate(args, start=1):
                if isinstance(arg, str):
                    continue
                if len(arg) < i:
                    continue
                new_tokens = encode_prepend_newline(self.tokenizer, arg[-i])
                length += len(new_tokens)
                if length > self.max_history_tokens:
                    return sum(merge_objects, [])
                merge_objects[j] = new_tokens + merge_objects[j]

        return sum(merge_objects, [])
