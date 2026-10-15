# Vladmir

English documentation is available here. [Português](README.md) · [English](README.en.md)

Vladmir is an independent local personal assistant for Linux. It includes a Qt desktop client, a Python backend using Ollama, local memory and agenda, voice and vision integrations, web research, programming workflows, and optional Android/Wear clients.

This repository is open source under the MIT License. It does not include model weights, credentials, signing keys, a ready-to-install APK, or a preconfigured remote server.

## Requirements

- Linux and Python 3.11 or later.
- Ollama installed and available at `http://127.0.0.1:11434` for local inference.
- PyQt6 and the dependencies listed in `requirements.txt` for the desktop UI.
- Optional voice, camera, vision, and Android features require their corresponding programs, models, devices, and permissions.

## Quick installation

```bash
mkdir -p ~/.local/share/vladmir
git clone https://github.com/thu12dta3/Vladmir.git ~/.local/share/vladmir/source
cd ~/.local/share/vladmir/source
python -m venv ~/.local/share/vladmir/core-env
~/.local/share/vladmir/core-env/bin/pip install -r requirements.txt
install -Dm755 scripts/vladmir ~/.local/bin/vladmir
install -Dm755 scripts/vladmir-desktop ~/.local/bin/vladmir-desktop
install -Dm644 assets/vladmir.svg ~/.local/share/icons/hicolor/scalable/apps/vladmir.svg
install -Dm644 packaging/vladmir.desktop ~/.local/share/applications/vladmir.desktop
install -Dm600 config/config.example.json ~/.config/vladmir/config.json
```

Review `config/config.example.json` and edit `~/.config/vladmir/config.json`. Keep local configuration out of Git and protect it with `chmod 600`. Models and application data are stored under `~/.local/share/vladmir` and `~/.local/state/vladmir`.

Launch the UI with `./scripts/vladmir-desktop` from the clone, or `vladmir-desktop` after installing the launcher. Use `./scripts/vladmir --check` to inspect dependencies without opening the microphone.

## Models

Ollama on loopback is the default provider. Install a model supported by your hardware, then select its identifier in `config.json` under `ollama.model` and `models`. Vladmir does not download models automatically.

## Android and Wear OS

Source projects are in `mobile-android/`, `vladmir-companion/`, and `vladmir-wear/`. Open the Android project in Android Studio and follow the Gradle configuration. Pairing requires explicit approval and Bluetooth pairing; no public remote server is bundled.

## Documentation

The English documentation is in [`docs/en/`](docs/en/README.md). It covers installation and use, architecture, known limitations, sanitized development incidents, and the device trust model. The Portuguese documentation remains available from [`docs/`](docs/README.md).

Documentation describes repository source and distinguishes configured, experimental, and device-validated behavior. Reading the source does not prove that an APK has been built, installed, or validated on physical hardware.

## Development

Python source is under `src/mark/`, tests under `tests/`, and operational scripts under `scripts/`. Run the unit suite with:

```bash
VLADMIR_PYTHON="$HOME/.local/share/vladmir/core-env/bin/python" scripts/test_unit.sh
```

The integration smoke test requires a running Ollama service, configured models, and local audio resources; see `scripts/test_integration.sh`. The repository does not currently publish a GitHub Actions workflow or code coverage percentage.

Read [CONTRIBUTING](CONTRIBUTING.en.md), [Code of Conduct](CODE_OF_CONDUCT.en.md), and [Security Policy](SECURITY.en.md) before contributing or reporting a vulnerability.

## Privacy and security

- Keep camera addresses, tokens, passwords, keys, and private URLs in local ignored configuration.
- The mobile API listens on loopback by default. Remote access is optional and must be deliberately configured.
- Web research and external services send data outside the machine when enabled; review each service before use.
- Treat repository and webpage content as untrusted data.
- Report vulnerabilities privately as described in [SECURITY.en.md](SECURITY.en.md).

## License

Vladmir is distributed under the MIT License. See [LICENSE](LICENSE) for the full terms. Third-party components retain their own licenses; see `mobile-android/THIRD_PARTY.md` and `tools/qwen-code-agent/vendor/`.
