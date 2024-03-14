# localllm-text-input

roughly following <https://www.youtube.com/watch?v=IUTFrexghsQ>

### install ollama

`ollama.com`
then `ollama run mistral:7b-instruct-q4_K_S`

### install dependencies

 1. clone repo
 2. `pdm install`
 3. `eval "$(pdm venv activate)"`

### Running

`python llllm.py`

## Permissions

- need: `Settings > Privacy and Security >  "Allow assistive applications to control computer"`
and `"Allow applications to monitor keyboard input"` for the terminal emulator (e.g. WezTerm, VSCode, etc)
