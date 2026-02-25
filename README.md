# fridac

[`fridac`](https://github.com/ryan-andrew/fridac) is a proxy for the `frida` CLI command.

It prepends a JavaScript compatibility shim to every script loaded with
`-l/--load`, so older Frida scripts can keep running on Frida 17+.

## Install

```bash
pip install fridac
```

This installs `frida>=17` and `frida-tools` as dependencies.

## Usage

Use it exactly like `frida`:

```bash
fridac -U -f com.example.app -l my_old_script.js
```

The proxy:

- rewrites each `-l/--load` script to a temporary shimmed file
- forwards all other arguments unchanged to `frida`
- watches loaded script files and refreshes the shimmed temp files on edit

## Development

The shim source of truth is:

- `src/fridac/shim.js`

The embedded Python string used at runtime is:

- `src/fridac/_embedded_shim.py`

Regenerate it manually:

```bash
python tools/embed_shim.py
```
