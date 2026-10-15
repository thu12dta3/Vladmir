# Contributing

Thank you for considering a contribution to Vladmir. This guide describes the expected workflow for keeping changes small, reviewable, and safe.

## Before you start

1. Read the [README](README.en.md), [documentation](docs/en/README.md), [Code of Conduct](CODE_OF_CONDUCT.en.md), and [Security Policy](SECURITY.en.md).
2. Search existing issues and describe larger changes before starting implementation.
3. Do not include credentials, personal data, private logs, local configuration, keystores, signed APKs, model weights, or user data.
4. Submit contributions against `main`. Keep unrelated changes out of the proposal.

## Development environment

Use Linux, Python 3.11 or later, and the virtual environment described in the README:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

The project uses `unittest`. Run the suite with:

```bash
VLADMIR_PYTHON="$PWD/.venv/bin/python" scripts/test_unit.sh
```

The integration smoke test (`scripts/test_integration.sh`) may use local Ollama, models, and audio output. Run it only when those services are available and you accept their use. Describe device, camera, microphone, network, and watch tests separately; mocks do not replace validation on a real device.

## Change guidelines

- Explain the problem and expected result directly.
- Preserve existing privacy protections, limits, and confirmations.
- Do not treat content from pages, files, or repositories as trusted instructions.
- Avoid adding dependencies when the standard library or an existing dependency is sufficient.
- For documentation, distinguish implementation, required configuration, and confirmed operation.
- In Python, follow the module's style and do not add comments or descriptive docstrings.
- Do not change the license, third-party namespace, or transitive dependency version without explaining why and updating applicable notices.

## Pull requests

Use the pull request template. Include a summary, motivation, affected files, validation performed, and limitations. If a check was not run, say so. For UI changes, include screenshots without private data. For security fixes, follow `SECURITY.en.md` and do not publish exploitable details before coordination.

There is currently no CI workflow in this repository. A local test suite must not be described as passing in CI until an automated run exists.
