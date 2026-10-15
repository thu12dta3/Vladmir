# Local configuration

Use `config.example.json` as a reference to create `~/.config/vladmir/config.json`. Do not add the active file to Git; use permissions `0600`. Do not put passwords in logs or examples.

Data is stored under `~/.local/share/vladmir` and `~/.local/state/vladmir`. `VLADMIR_CONFIG` points to a different configuration file. Vladmir uses environment variables prefixed with `VLADMIR_`; it does not read MARK configuration or credentials.

Ollama uses `http://127.0.0.1:11434` by default. Camera URL, credentials, and ports must be configured only on the local machine; the example has no camera host. Web research and external providers can be disabled in configuration.

[Português](README.md) · [English](README.en.md)
