# coding: utf-8

"""Utility functions for dealing with natural language processing.

A lot of stuff was removed from here, because at that time it all seemed unnecessary.
Look at AI Dungeon 2: Clover Edition for more utility functions.
"""
import re


def pad_text(text, width, sep=' '):
    while len(text) < width:
        text += sep
    return text


def format_input(text):
    """
    Formats the text for purposes of storage.
    """
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def format_result(text):
    """
    Formats the result text from the AI to be more human-readable.
    """
    text = re.sub(r"\n{3,}", "<br>", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"<br>", "\n", text)
    text = re.sub(r"(\"[.!?]) ([A-Z])", "\\1\n\n\\2", text)
    text = re.sub(r"([^\"][.!?]) \"", "\\1\n\n\"", text)
    text = re.sub(r"([\".!?]) \"", "\\1\n\"", text)
    return text.strip()


def _get_prefix(first_string ,second_string):
    if not first_string or not second_string:
        return ""
    if first_string == second_string:
        return first_string
    maximum_length = min(len(first_string), len(second_string))
    for i in range(0, maximum_length):
        if not first_string[i] == second_string[i]:
            return first_string[0:i]
    return first_string[0:maximum_length]


def get_similarity(first_string, second_string, scaling=0.1):
    first_string_length = len(first_string)
    second_string_length = len(second_string)
    a_matches = [False] * first_string_length
    b_matches = [False] * second_string_length
    matches = 0
    transpositions = 0
    jaro_distance = 0.0

    if first_string_length == 0 or second_string_length == 0:
        return 1.0

    maximum_matching_distance = (max(first_string_length, second_string_length) // 2) - 1
    if maximum_matching_distance < 0:
        maximum_matching_distance = 0

    for i in range (first_string_length):
        start = max(0, i - maximum_matching_distance)
        end = min(i + maximum_matching_distance + 1, second_string_length)
        for x in range (start, end):
            if b_matches[x]:
                continue
            if first_string[i] != second_string[x]:
                continue
            a_matches[i] = True
            b_matches[x] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(first_string_length):
        if not a_matches[i]:
            continue
        while not b_matches[k]:
            k += 1
        if first_string[i] != second_string[k]:
            transpositions += 1
        k += 1

    jaro_distance = ((matches / first_string_length) +
                    (matches / second_string_length) +
                    ((matches - transpositions / 2) / matches)) / 3.0
    prefix = min(len(_get_prefix(first_string, second_string)), 4)

    # Round to 2 places of percision to match pyjarowinkler formatting
    return round((jaro_distance + prefix * scaling * (1.0 - jaro_distance)) * 100.0) / 100.0


def cut_trailing_action(text):
    lines = text.split("\n")
    last_line = lines[-1]
    if (
        "you ask" in last_line
        or "You ask" in last_line
        or "you say" in last_line
        or "You say" in last_line
    ) and len(lines) > 1:
        text = "\n".join(lines[0:-1])
    return text


def fix_trailing_quotes(text):
    num_quotes = text.count('"')
    if num_quotes % 2 == 0:
        return text
    else:
        return text + '"'


def cut_trailing_sentence(text, allow_action=False):
    text = standardize_punctuation(text)
    last_punc = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    if last_punc <= 0:
        last_punc = len(text) - 1
    et_token = text.find("<")
    if et_token > 0:
        last_punc = min(last_punc, et_token - 1)
    if allow_action:
        act_token = text.find(">")
        if act_token > 0:
            last_punc = min(last_punc, act_token - 1)
    text = text[: last_punc + 1]
    text = fix_trailing_quotes(text)
    if allow_action:
        text = cut_trailing_action(text)
    return text


def capitalize(word):
    return word[0].upper() + word[1:]


def standardize_punctuation(text):
    text = text.replace("’", "'")
    text = text.replace("`", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')
    return text
