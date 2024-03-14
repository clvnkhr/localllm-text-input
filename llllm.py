import argparse
from pynput import keyboard
from pynput.keyboard import Key, Controller
import pyperclip
import time
import httpx
from string import Template

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

# post request example to test API
# curl -X POST http://localhost:11434/api/generate -d '{
#   "model": "mistral:7b-instruct-q4_K_S",
#   "prompt":"Here is a story about llamas eating grass",
#   "stream": false
#  }'


def fix(text: str, client: httpx.Client) -> str:
    prompt = FIX_PROMPT_TEMPLATE.substitute(text=text)
    response = client.post(
        OLLAMA_ENDPOINT,
        json={"prompt": prompt, **OLLAMA_CONFIG},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        return text + f"!ERROR{response.status_code}"
    return response.json()["response"].strip()


def fix_current_line(client: httpx.Client, vim_mode: bool = False) -> None:
    # on mac, select line by pressing cmd + shift + left
    if vim_mode:
        _ = [controller.tap(k) for k in "0v$"]
    else:
        keys = [Key.cmd, Key.shift, Key.left]
        _ = [controller.press(k) for k in keys]
        _ = [controller.release(k) for k in keys]
    fix_selection(client)


def fix_selection(client: httpx.Client, vim_mode: bool = False) -> None:
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
    pyperclip.copy(fix(text, client))
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
            str(Key.f9.value): (lambda: fix_selection(client, vim_mode=args.vim)),
            str(Key.f10.value): (lambda: fix_current_line(client, vim_mode=args.vim)),
        }

    with (
        httpx.Client(timeout=None) as c,
        keyboard.GlobalHotKeys(hotkeys=hotkeys(c)) as h,
    ):
        h.join()
