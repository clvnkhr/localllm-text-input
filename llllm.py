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
PROMPT_TEMPLATE = Template(
    """Fix all typos, the casing, and the punctuation in the following text, \
but preserve all the newline characters. \
Do not modify LaTeX code or introduce escape characters. \
Return only the corrected text, do not include a preamble and do not place the text in a code block:\
    
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
    prompt = PROMPT_TEMPLATE.substitute(text=text)
    response = client.post(
        OLLAMA_ENDPOINT,
        json={"prompt": prompt, **OLLAMA_CONFIG},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        return text + f"!ERROR{response.status_code}"
    return response.json()["response"].strip()


def fix_current_line(client: httpx.Client) -> None:
    # on mac, select line by pressing cmd + shift + left
    keys = [Key.cmd, Key.shift, Key.left]
    _ = [controller.press(k) for k in keys]
    _ = [controller.release(k) for k in keys]
    fix_selection(client)


def fix_selection(client: httpx.Client) -> None:
    with controller.pressed(Key.cmd):
        controller.tap("c")
    time.sleep(0.1)
    text = pyperclip.paste()
    pyperclip.copy(fix(text, client))
    time.sleep(0.1)
    with controller.pressed(Key.cmd):
        controller.tap("v")


if __name__ == "__main__":
    with httpx.Client(timeout=None) as client:
        with keyboard.GlobalHotKeys(
            {
                str(Key.f9.value): (lambda: fix_selection(client)),
                str(Key.f10.value): (lambda: fix_current_line(client)),
            },
        ) as h:
            h.join()