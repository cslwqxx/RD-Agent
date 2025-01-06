"""
This is some common utils functions.
it is not binding to the scenarios or framework (So it is not placed in rdagent.core.utils)
"""

# TODO: merge the common utils in `rdagent.core.utils` into this folder
# TODO: split the utils in this module into different modules in the future.

import importlib
import json
import re
import sys
from types import ModuleType
from typing import Union

from rdagent.oai.llm_utils import APIBackend
from rdagent.utils.agent.tpl import T


def get_module_by_module_path(module_path: Union[str, ModuleType]):
    """Load module from path like a/b/c/d.py or a.b.c.d

    :param module_path:
    :return:
    :raises: ModuleNotFoundError
    """
    if module_path is None:
        raise ModuleNotFoundError("None is passed in as parameters as module_path")

    if isinstance(module_path, ModuleType):
        module = module_path
    else:
        if module_path.endswith(".py"):
            module_name = re.sub("^[^a-zA-Z_]+", "", re.sub("[^0-9a-zA-Z_]", "", module_path[:-3].replace("/", "_")))
            module_spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(module_spec)
            sys.modules[module_name] = module
            module_spec.loader.exec_module(module)
        else:
            module = importlib.import_module(module_path)
    return module


def convert2bool(value: Union[str, bool]) -> bool:
    """
    Motivation: the return value of LLM is not stable. Try to convert the value into bool
    """
    # TODO: if we have more similar functions, we can build a library to converting unstable LLM response to stable results.
    if isinstance(value, str):
        v = value.lower().strip()
        if v in ["true", "yes", "ok"]:
            return True
        if v in ["false", "no"]:
            return False
        raise ValueError(f"Can not convert {value} to bool")
    elif isinstance(value, bool):
        return value
    else:
        raise ValueError(f"Unknown value type {value} to bool")

def remove_ansi_codes(s: str) -> str:
    """
    It is for removing ansi ctrl characters in the string(e.g. colored text)
    """
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", s)


def filter_progress_bar(stdout: str) -> str:
    """
    Filter out progress bars from stdout using regex.
    """
    # Initial progress bar regex pattern
    progress_bar_re = (
        r"(\d+/\d+\s+[━]+\s+\d+s?\s+\d+ms/step.*?\u0008+|"
        r"\d+/\d+\s+[━]+\s+\d+s?\s+\d+ms/step|"
        r"\d+/\d+\s+[━]+\s+\d+s?\s+\d+ms/step.*|"
        r"\d+/\d+\s+[━]+.*?\u0008+|"
        r"\d+/\d+\s+[━]+.*|[ ]*\u0008+)"
    )

    filtered_stdout = remove_ansi_codes(stdout)
    filtered_stdout = re.sub(progress_bar_re, "", filtered_stdout)
    filtered_stdout = re.sub(r'\s*\n\s*', '\n', filtered_stdout)

    # Check if progress bars are already filtered
    system_prompt = T(".prompts:if_filtered.system").r()
    user_prompt = T(".prompts:if_filtered.user").r(
        filtered_stdout=filtered_stdout,
    )
    if_filtered_stdout = json.loads(
        APIBackend().build_messages_and_create_chat_completion(user_prompt, system_prompt, json_mode=True)
    ).get("progress bar filtered", False)

    if convert2bool(if_filtered_stdout):
        return filtered_stdout

    # Attempt further filtering up to 5 times
    for _ in range(5):
        system_prompt = T(".prompts:filter_progress_bar.system").r()
        user_prompt = T(".prompts:filter_progress_bar.user").r(
            stdout=filtered_stdout,
        )

        new_pattern = json.loads(
            APIBackend().build_messages_and_create_chat_completion(
                user_prompt=user_prompt, system_prompt=system_prompt, json_mode=True
            )
        )["regex pattern"]

        filtered_stdout = re.sub(new_pattern, "", filtered_stdout)
        filtered_stdout = re.sub(r'\s*\n\s*', '\n', filtered_stdout)

        system_prompt = T(".prompts:if_filtered.system").r()
        user_prompt = T(".prompts:if_filtered.user").r(
            filtered_stdout=filtered_stdout,
        )
        if_filtered_stdout = json.loads(
            APIBackend().build_messages_and_create_chat_completion(user_prompt, system_prompt, json_mode=True)
        ).get("progress bar filtered", False)

        if convert2bool(if_filtered_stdout):
            break

    return filtered_stdout