# Vladmir

Vladmir é um assistente pessoal local com chat para desktop, voz, memória compartilhada, ferramentas, visão, agenda, integração opcional com celular e relógio, pesquisa web e fluxos de programação. É um projeto independente mantido separadamente.

Contato: thu12dta3@tutamail.com

## Requisitos

- Linux com Python 3.11 ou superior.
- Ollama instalado e acessível em http://127.0.0.1:11434 para inferência local.
- PyQt6 e dependências listadas em requirements.txt para a interface.
- Recursos opcionais de voz, câmera, visão e integração Android exigem programas e permissões correspondentes.

O Vladmir não inclui pesos de modelos, credenciais, chaves de assinatura ou um endpoint Tailscale pré-configurado. Selecione modelos compatíveis no Ollama e configure integrações opcionais localmente.

## Instalação rápida

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

Use config/config.example.json como referência e crie ~/.config/vladmir/config.json com os valores que pretende usar. O arquivo fica fora do repositório; proteja-o com chmod 600. Modelos e dados ficam sob ~/.local/share/vladmir e ~/.local/state/vladmir.

Inicie a interface pelo clone com ./scripts/vladmir-desktop ou execute vladmir-desktop após instalar o launcher em ~/.local/bin. Ele usa o ambiente Python em ~/.local/share/vladmir/core-env. O assistente de voz pode ser iniciado com ./scripts/vladmir. Para conferir dependências sem abrir o microfone, use ./scripts/vladmir --check.

## Modelos

O Vladmir usa Ollama em loopback por padrão. Instale somente um modelo que seu hardware suporte e selecione seu identificador em config.json, nas chaves ollama.model e models. O projeto não baixa modelos automaticamente.

## Android e Wear OS

O código-fonte dos aplicativos está em mobile-android/, vladmir-companion/ e vladmir-wear/. Abra mobile-android/ no Android Studio e compile as variantes desejadas. O vínculo requer aprovação explícita no Android e Bluetooth pareado; nenhum servidor remoto público vem embutido.

## Documentação detalhada

Os guias de uso, capacidades/arquitetura e limitações/roteiro de melhorias estão em [docs/](docs/README.md). Cada guia está disponível em Markdown, texto simples e PDF A4 preto e branco. A documentação descreve o código-fonte e diferencia recursos configuráveis, experimentais e dependentes de validação no dispositivo.

## Privacidade e segurança

- Endereços de câmera, tokens, senhas, chaves e URLs privadas ficam em configuração local ignorada pelo Git.
- A API móvel escuta em loopback por padrão. Exposição remota é opcional e deve ser configurada pelo operador.
- Pesquisa web e serviços externos só são usados pelas integrações habilitadas localmente.
- O conteúdo de repositórios e páginas externas é tratado como dado não confiável.
- Consulte SECURITY.md para reportar vulnerabilidades.

## Licença

O código do Vladmir é distribuído sob a licença MIT; consulte LICENSE para os termos completos. Isso permite usar, modificar e redistribuir o projeto, inclusive em produtos comerciais, desde que o aviso de copyright e a licença acompanhem cópias substanciais. Componentes de terceiros mantêm suas próprias licenças; consulte mobile-android/THIRD_PARTY.md e tools/qwen-code-agent/vendor/.
