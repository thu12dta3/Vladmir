# Como contribuir

Idiomas: [Português](CONTRIBUTING.md) · [English](CONTRIBUTING.en.md)

Obrigado por considerar uma contribuição ao Vladmir. Este guia descreve o fluxo esperado para manter mudanças pequenas, revisáveis e seguras.

## Antes de começar

1. Leia o [README](README.md), a documentação em [`docs/`](docs/README.md), o [código de conduta](CODE_OF_CONDUCT.md) e a [política de segurança](SECURITY.md).
2. Procure issues existentes e descreva o problema antes de iniciar uma mudança grande.
3. Não inclua credenciais, dados pessoais, logs privados, arquivos de configuração local, keystores, APKs assinados, pesos de modelos ou dados de usuários.
4. Abra contribuições contra `main`. Não inclua alterações sem relação com a proposta.

## Ambiente de desenvolvimento

Use Linux, Python 3.11 ou superior e o ambiente virtual descrito no README. Para instalar dependências Python:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

O projeto usa `unittest`. Para executar a suíte, use o interpretador do ambiente:

```bash
VLADMIR_PYTHON="$PWD/.venv/bin/python" scripts/test_unit.sh
```

O smoke test de integração (`scripts/test_integration.sh`) pode falar com Ollama, modelo e saída de áudio locais. Só o execute se esses serviços estiverem disponíveis e você aceitar o uso deles. Testes de dispositivo, câmera, microfone, rede ou relógio devem ser descritos separadamente; mock não substitui validação no dispositivo real.

## Diretrizes de mudança

- Explique o problema e o resultado esperado em linguagem direta.
- Mantenha limites, confirmações e proteções de privacidade já existentes.
- Não transforme conteúdo de páginas, arquivos ou repositórios em instruções confiáveis.
- Evite adicionar dependências quando a biblioteca padrão ou uma dependência existente resolver.
- Para documentação, diferencie implementação no código, configuração necessária e funcionamento confirmado.
- Em código Python, preserve o estilo do módulo e não acrescente comentários ou docstrings descritivos.
- Não altere licença, namespace de terceiros ou versão de dependência transitiva sem explicar o motivo e atualizar os avisos aplicáveis.

## Pull request

Use o modelo de pull request. Inclua resumo, motivação, arquivos afetados, validação executada e limitações. Se não rodou um teste, diga isso explicitamente. Para mudanças de interface, inclua capturas sem dados privados; para correções de segurança, siga `SECURITY.md` e não publique detalhes exploráveis antes da coordenação.

Não há atualmente workflow de CI neste repositório. A suíte local não deve ser descrita como aprovada por CI até existir execução automatizada registrada.
