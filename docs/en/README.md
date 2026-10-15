# Vladmir documentation

This documentation describes the source published in Vladmir. The presence of a screen, endpoint, or module proves that a corresponding implementation exists in the repository; it does not prove installation or validation on every computer, phone, or watch.

## Documents

| Document | Markdown | Plain text | Black-and-white PDF | Portuguese |
|---|---|---|---|---|
| Installation and usage guide | [MD](INSTALLATION_AND_USAGE.md) | [TXT](INSTALLATION_AND_USAGE.txt) | [PDF](pdf/INSTALLATION_AND_USAGE.pdf) | [Português](../GUIA_DE_USO.md) |
| Capabilities and architecture | [MD](CAPABILITIES_AND_ARCHITECTURE.md) | [TXT](CAPABILITIES_AND_ARCHITECTURE.txt) | [PDF](pdf/CAPABILITIES_AND_ARCHITECTURE.pdf) | [Português](../CAPACIDADES_E_ARQUITETURA.md) |
| Limitations and improvement plan | [MD](LIMITATIONS_AND_IMPROVEMENTS.md) | [TXT](LIMITATIONS_AND_IMPROVEMENTS.txt) | [PDF](pdf/LIMITATIONS_AND_IMPROVEMENTS.pdf) | [Português](../LIMITACOES_E_MELHORIAS.md) |
| Sanitized incidents and evidence | [MD](SANITIZED_INCIDENTS_AND_EVIDENCE.md) | [TXT](SANITIZED_INCIDENTS_AND_EVIDENCE.txt) | [PDF](pdf/SANITIZED_INCIDENTS_AND_EVIDENCE.pdf) | [Português](../INCIDENTES_E_EVIDENCIAS_SANITIZADOS.md) |
| Device trust model | [MD](DEVICE_TRUST_MODEL.md) | [TXT](DEVICE_TRUST_MODEL.txt) | [PDF](pdf/DEVICE_TRUST_MODEL.pdf) | [Português](../MODELO_DE_CONFIANCA_DISPOSITIVOS.md) |
| Pending Home Assistant integration | [MD](HOME_ASSISTANT_INTEGRATION_PENDING.md) | [TXT](HOME_ASSISTANT_INTEGRATION_PENDING.txt) | [PDF](pdf/HOME_ASSISTANT_INTEGRATION_PENDING.pdf) | [Português](../INTEGRACAO_HOME_ASSISTANT_PENDENTE.md) |

## How to interpret the documents

- **Implemented in code:** a corresponding module, screen, or route exists in the repository.
- **Configuration-dependent:** requires a service, model, device, permission, or locally configured credential.
- **Experimental or partial:** a flow exists, but broader validation, automation, or persistence is missing.
- **Pending:** the current implementation does not provide the behavior or still depends on an integration that does not exist.

These documents were prepared from static inspection of `main` on October 14, 2026. They do not replace execution on a computer or physical device. Also consult the [English README](../../README.en.md), [configuration guide](../../config/README.md), [security policy](../../SECURITY.en.md), `mobile-android/README.md`, and third-party notices.

The Python source is under `src/mark/`; the repository has a `unittest` suite under `tests/`. It does not currently publish a GitHub Actions workflow or a coverage percentage. Governance files and templates are available in [English](../../CONTRIBUTING.en.md) and [Portuguese](../../CONTRIBUTING.md).

The sanitized incidents appendix derives from internal reports about the related MARK project and explicitly distinguishes those records from Vladmir validation. Raw logs, original images, credentials, and private configuration were not published.
