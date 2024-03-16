import argparse
import time
from string import Template
from typing import Callable

from pynput import keyboard
from pynput.keyboard import Key, Controller
import pyperclip
import httpx


controller = Controller()
httpx.Timeout(connect=5, read=None, write=5, pool=5)

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_CONFIG = dict(
    model="mistral:7b-instruct-q4_K_S",
    keep_alive="5m",
    stream=False,
)
FIX_PROMPT_TEMPLATE = Template(
    """Fix all typos, the casing, and the punctuation in the following text, \
but preserve all the newline characters. \
Do not modify LaTeX code or introduce escape characters. \
Return only the corrected text, do not include a preamble, \
and do not place the text in a code block:\

$text
"""
)

IMPROVE_PROMPT_TEMPLATE = Template(
    """Rewrite this text using professional english suitable \
for publication in a mathematical research journal. \
Do not modify LaTeX code or introduce escape characters. \
Return only the corrected text, do not include a preamble, \
and do not place the text in a code block:\

$text
"""
)


def _test_api():
    "Post request example to test API. this is just here for me to easily copy..."
    return """
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "mistral:7b-instruct-q4_K_S",
  "prompt":"Here is a story about llamas eating grass",
  "stream": false
 }'
"""


def fix(text: str, client: httpx.Client) -> str:
    return ask(client, prompt=FIX_PROMPT_TEMPLATE.substitute(text=text))


def improve(text: str, client: httpx.Client) -> str:
    return ask(client, prompt=IMPROVE_PROMPT_TEMPLATE.substitute(text=text))


def ask(client: httpx.Client, prompt: str) -> str:
    """Fixes typos in text by asking the ollama client."""
    response = client.post(
        OLLAMA_ENDPOINT,
        json={"prompt": prompt, **OLLAMA_CONFIG},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        return f"!ERROR{response.status_code}, {prompt=}"
    return response.json()["response"].strip()


def on_current_line(
    act: Callable[[str, httpx.Client], str],
    client: httpx.Client,
    vim_mode: bool = False,
) -> None:
    """Selects the current line and calls the `fix_selection` function, passing the `client` as an
    argument."""

    if vim_mode:
        # 0  = go to beginning of line
        # v$ = visual selection to end of line
        _ = [controller.tap(k) for k in "0v$"]
    else:
        # on mac, (cmd <-) = go to beginning of line
        # (cmd shift ->)   = visual selection to end of line
        with controller.pressed(Key.cmd):
            controller.tap(Key.right)
            with controller.pressed(Key.shift):
                controller.tap(Key.left)
    on_selection(act, client, vim_mode=vim_mode)


def on_selection(
    act: Callable[[str, httpx.Client], str],
    client: httpx.Client,
    vim_mode: bool = False,
) -> None:
    """Yanks the selection,
    puts the clipboard into python with pyperclip,
    uses the callback act on the text (passing client on),
    and pastes with pyperclip."""

    def yank():
        if vim_mode:
            controller.tap("y")  # y = yank in visual mode
        else:
            with controller.pressed(Key.cmd):
                controller.tap("c")

    def paste():
        if vim_mode:
            # gvp = repeat previous selection then paste
            _ = [controller.tap(k) for k in "gvp"]
        else:
            with controller.pressed(Key.cmd):
                controller.tap("v")

    yank()
    time.sleep(0.1)
    text = pyperclip.paste()
    if not text:
        # empty yank indicates some sort of error.
        print("empty yank")
        return
    pyperclip.copy(act(text, client))
    time.sleep(0.1)
    paste()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--vim",
        action="store_true",
        help="Enable Vim mode (yanking instead of cmd-c, etc)",
    )
    args = parser.parse_args()

    def hotkeys(client: httpx.Client):
        return {
            str(Key.f9.value): (lambda: on_selection(fix, client, vim_mode=args.vim)),
            # str(Key.f10.value): (
            #     lambda: on_current_line(fix, client, vim_mode=args.vim)
            # ),
            str(Key.f10.value): (
                lambda: on_selection(improve, client, vim_mode=args.vim)
            ),
            # str(Key.f8.value): (
            #     lambda: on_current_line(improve, client, vim_mode=args.vim)
            # ),
        }

    with (
        httpx.Client(timeout=None) as c,
        keyboard.GlobalHotKeys(hotkeys=hotkeys(c)) as h,
    ):
        h.join()
