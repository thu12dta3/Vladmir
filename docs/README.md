# Documentação do Vladmir

Este conjunto descreve o estado do código-fonte publicado no Vladmir. A presença de uma tela, endpoint ou módulo comprova implementação no repositório, mas não significa que o recurso foi instalado ou validado em todo computador, celular ou relógio.

## Documentos

| Documento | Markdown | Texto simples | PDF preto e branco |
|---|---|---|---|
| Guia de instalação e uso | [GUIA_DE_USO.md](GUIA_DE_USO.md) | [GUIA_DE_USO.txt](GUIA_DE_USO.txt) | [GUIA_DE_USO.pdf](pdf/GUIA_DE_USO.pdf) |
| Capacidades e arquitetura | [CAPACIDADES_E_ARQUITETURA.md](CAPACIDADES_E_ARQUITETURA.md) | [CAPACIDADES_E_ARQUITETURA.txt](CAPACIDADES_E_ARQUITETURA.txt) | [CAPACIDADES_E_ARQUITETURA.pdf](pdf/CAPACIDADES_E_ARQUITETURA.pdf) |
| Limitações e plano de melhorias | [LIMITACOES_E_MELHORIAS.md](LIMITACOES_E_MELHORIAS.md) | [LIMITACOES_E_MELHORIAS.txt](LIMITACOES_E_MELHORIAS.txt) | [LIMITACOES_E_MELHORIAS.pdf](pdf/LIMITACOES_E_MELHORIAS.pdf) |
| Incidentes e evidências sanitizados | [INCIDENTES_E_EVIDENCIAS_SANITIZADOS.md](INCIDENTES_E_EVIDENCIAS_SANITIZADOS.md) | [INCIDENTES_E_EVIDENCIAS_SANITIZADOS.txt](INCIDENTES_E_EVIDENCIAS_SANITIZADOS.txt) | [INCIDENTES_E_EVIDENCIAS_SANITIZADOS.pdf](pdf/INCIDENTES_E_EVIDENCIAS_SANITIZADOS.pdf) |

## Como interpretar

- **Implementado no código**: há módulo, tela ou rota correspondente no repositório.
- **Dependente de configuração**: exige serviço, modelo, dispositivo, permissão ou credencial configurada localmente.
- **Experimental ou parcial**: há fluxo implementado, mas faltam validação ampla, automação ou persistência.
- **Pendente**: a implementação atual não oferece o comportamento prometido ou depende de uma integração que ainda não existe.

Os documentos foram preparados por inspeção estática do repositório `main` em 14 de outubro de 2026. Isso não substitui execução no computador ou teste físico dos dispositivos. Para requisitos, instalação e segurança, também consulte [README.md](../README.md), [config/README.md](../config/README.md), [SECURITY.md](../SECURITY.md), `mobile-android/README.md` e os avisos de terceiros.

O código Python está em `src/mark/` e há suíte `unittest` em `tests/`; o projeto ainda não publica workflow de CI nem percentual de cobertura. A documentação de contribuição e governança está em [CONTRIBUTING.md](../CONTRIBUTING.md) e [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md). A estrutura e esses fatos foram conferidos no commit `d9b3358` antes desta atualização.

Ainda não há workflow GitHub Actions; não há badge de build porque não existe execução de CI para reportar. Os arquivos de issue/PR ajudam a coletar relatos, mas não significam que há equipe de suporte ou SLA estabelecido.

O apêndice de [incidentes e evidências sanitizados](INCIDENTES_E_EVIDENCIAS_SANITIZADOS.md) deriva de relatórios internos do MARK e separa explicitamente esses registros da validação do Vladmir. Logs brutos, imagens originais, credenciais e configurações privadas não foram publicados.
