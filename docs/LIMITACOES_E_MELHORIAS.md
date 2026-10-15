# Limitações, defeitos conhecidos e plano de melhorias

**Base:** inspeção estática do código em `main` em 14/10/2026. Os itens abaixo não afirmam que um bug foi reproduzido em uma instalação. “Defeito/risco observado” descreve limite explícito ou lacuna visível no código. Prioridades são recomendações, não compromisso de prazo.

## Como priorizar

- **P0 — bloqueador de confiança:** risco de perda de dados, exposição de credencial, corrupção ou instalação insegura.
- **P1 — estabilidade:** conectividade, operação contínua, áudio/vídeo e recuperação de erro.
- **P2 — capacidade:** limites e integração incompleta.
- **P3 — acabamento:** telemetria, documentação e experiência.

## Matriz de lacunas

| Prioridade | Área | Limitação observada | Impacto prático | Solução recomendada |
|---|---|---|---|---|
| P1 | Companion → Wear | A própria tela de diagnóstico informa que reconexão automática ainda não está habilitada. | Celular bloqueado, processo suspenso ou perda de Bluetooth pode deixar o relógio offline. | Implementar reconexão com ciclo de vida Android, backoff, foreground service/notificação persistente quando permitido, teste com tela apagada e políticas de bateria de fabricantes. |
| P1 | Chamada | Voz é processada por turnos e depende de Whisper/Piper; não é stream duplex em tempo real. | Pausas e latência; interrupção e resposta natural podem variar. | Projetar canal de áudio persistente com cancelamento, VAD/streaming e buffers; medir latência fim a fim, perda e eco antes de substituir o fluxo atual. |
| P1 | Áudio Bluetooth | Entrada de headset pode provocar perfil HFP/HSP e reduzir a música enquanto a chamada usa microfone Bluetooth. | Música perde estéreo/qualidade durante chamada. | Detectar rota/perfil, oferecer entrada do microfone separado e manter saída A2DP quando a pilha permitir; testar PipeWire, headset e Discord/voz simultaneamente. |
| P1 | Dispositivos | Verificação de configuração não é validação física de câmera, fone, USB ou relógio. | Interface pode afirmar que existe fonte mesmo sem imagem ou áudio útil. | Exibir estado separado: configurado, enumerado, stream aberto e amostra válida; oferecer diagnóstico com timestamp e dispositivo selecionado. |
| P1 | API móvel | Sessões dependem de telefone, API, TLS/endereço e estado de pareamento. Android pode suspender o Companion. | Offline intermitente ou chamadas que não iniciam em segundo plano. | Adotar máquina de estados, heartbeat barato, reconexão controlada, mensagem de erro por camada e ensaios prolongados com bloqueio/tela apagada. |
| P2 | Anexos do chat | 5 arquivos, 6 MiB por arquivo, 8 MiB total e 400 mil caracteres. | Grandes datasets e mídia não cabem; arquivo de 1 GB não é suportado. | Upload em streaming, armazenamento temporário com quotas, cancelamento e progresso; fazer análise por blocos e limpar temporários. Só elevar limite após medir RAM, disco e superfície de ataque. |
| P2 | Biblioteca | Extração é heterogênea e limitada; formatos binários ou digitalizados podem virar metadados, texto estático ou resultado parcial. | Busca pode não achar conteúdo que parece visualmente presente. | Informar método/percentual/páginas extraídas, oferecer OCR separado e fila de reprocessamento; manter referência à origem e confirmar trechos antes de responder. |
| P2 | AR móvel | ARCore opcional; mapa atual existe apenas enquanto a tela está aberta. | Reorientar/sair pode perder o mapa; aparelho incompatível não funciona. | Persistência local criptografada opcional, mapa incremental com orçamento/expiração e UI clara sobre suporte do ARCore; medir deriva e consumo antes de ativar por padrão. |
| P2 | Câmera e visão | Modelo vê frames amostrados; cadência e qualidade variam, sem gravação/rastreamento persistente. | Detalhes rápidos podem não ser detectados; baixa luz/foco afetam respostas. | Mostrar indicador de frame/idade/resolução, ajuste de frequência e foco; comparar amostras reais com métrica de latência e precisão. |
| P2 | Professor/Engenheiro | Especialização usa os modelos configurados; memória/contexto continuam limitados. | Retomada de um detalhe antigo pode falhar. | Resumo estruturado por conversa, seleção recuperável de memórias e controle de contexto; avaliações com conversas longas e referências explícitas. |
| P2 | Autoevolução | Gera experimentos isolados, mas não promove código automaticamente. Ciclos dependem de systemd e instalação/ativação opt-in. | Usuário pode esperar que “Iniciar” funcione quando serviço ainda não foi preparado, ou interpretar candidato como mudança já aplicada. | Mostrar estado distinto “não instalado / parado / rodando / aguardando / candidato para revisão”; manter diff, rollback e métricas na tela. |
| P2 | Treino | QLoRA depende de contrato, dataset aprovado, holdout, GPU e medição. Não altera modelo ativo. | Pode não iniciar sem pré-requisitos; resultado não garante inteligência geral. | Assistente de pré-voo, relatório de espaço/VRAM/energia, pausa/checkpoint e avaliação contra baseline; proibir promoção sem revisão. |
| P2 | Email | O recurso monta `mailto:` e abre um rascunho; não envia por SMTP/API diretamente. | A mensagem pode não abrir se app padrão estiver ausente; envio é manual. | Rotular como “Preparar rascunho”; se houver integração de envio futura, implementar OAuth/API oficial, cofre de segredo, tela de confirmação e registro local mínimo. |
| P2 | Agenda | Persistência em SQLite local, sem sincronização externa. | Lembretes não acompanham automaticamente outros calendários/dispositivos. | Exportação/importação ICS e integração OAuth opcional, com conflitos e fuso horário visíveis. |
| P2 | Plugins | Integrações são nativas; não existe marketplace genérico de plugins externos. | Não é possível instalar plugins como na loja do ChatGPT. | Definir API versionada, permissões por capacidade, sandbox, assinatura e desinstalação antes de criar marketplace. |
| P2 | JetBrains MCP | Depende do servidor local e de compatibilidade da IDE. A execução pode ler/modificar projeto conforme a ferramenta. | Conexão/lista de ferramentas pode falhar; ferramenta pode ter efeitos no workspace. | Mostrar schemas e plano antes da chamada, limites de timeout/saída, restrição por workspace e log de consentimento. |
| P2 | GitHub | Ações dependem de `gh`, rede, permissões e branch escolhidos; edição tem limites por arquivo. | Um repositório fora do escopo da conta não abre; mudanças remotas exigem cuidado. | Pré-visualizar diff, confirmar repo/branch/caminho e SHA, proteger contra conflito e oferecer backup/rollback. |
| P2 | Sentinel | Usa ClamAV, caminho selecionado e permissões do usuário. Não é EDR e não cobre automaticamente todos os discos/processos. | “Nenhuma detecção” não prova que todo sistema esteja limpo. | Exibir escopo, exclusões, assinatura/data e erro de acesso; oferecer agendamento somente após autorização e testar falsos positivos. |
| P3 | Estado e observabilidade | Diferentes subsistemas podem falhar por dependência externa e retornar mensagens genéricas. | Difícil saber se o erro é modelo, API, permissão, codec, rede ou dispositivo. | Correlacionar ID de requisição, etapa e causa sanitizada; não registrar prompts, arquivos, tokens ou áudio por padrão. |
| P3 | Instalação de pacotes | Backup da operação é inventário de pacotes, não snapshot completo; gerenciadores têm efeitos colaterais. | “Backup” não garante rollback integral do sistema. | Chamar de inventário, registrar comando/versão e oferecer instruções de reversão específicas do gerenciador; nunca prometer restauração total. |

## Riscos a validar antes de uso diário

1. **Integridade do estado local:** testar cópia/restauração de configuração, agenda, memória e biblioteca em outro diretório de usuário.
2. **Atualização:** verificar mudanças de esquema e preservar dados antigos antes de substituir a instalação.
3. **Áudio contínuo:** verificar que microfone fecha ao encerrar chamada e que a rota de saída não muda inesperadamente.
4. **API remota:** confirmar TLS, autenticação, revogação de dispositivo, limite de requisição e ausência de exposição pública acidental.
5. **Dispositivos Android:** testar tela desligada, reinício, revogação de permissão, reconexão, rotação e pouca bateria.
6. **Saída de modelos:** testar resposta vazia, timeout, conteúdo não confiável, chamadas de ferramentas e limite de contexto.
7. **Instalação:** confirmar diálogo de aprovação, cópia de inventário e ação realmente executada antes de declarar sucesso.

## Roteiro sugerido

### Fase A — confiabilidade básica

- Criar smoke tests automatizados de inicialização, API, chat e encerramento de microfone.
- Publicar saída de diagnóstico sanitizada que classifica dependência ausente, timeout e erro de permissão.
- Fazer backup e restauração documentados dos diretórios locais.
- Manter a API inacessível fora de loopback até configuração explícita de TLS/autenticação.

### Fase B — celular e relógio

- Estabelecer máquina de estados única de conexão, heartbeat e reconexão com backoff.
- Validar foreground service e restrições de bateria em mais de um fabricante Android.
- Testar notificações com conteúdo sensível oculto por padrão, WhatsApp e revogação do acesso.
- Separar dados de telemetria permitidos de conteúdo de conversas e notificações.

### Fase C — voz, visão e AR

- Medir latência por fase (captura, transcrição, geração, síntese, reprodução).
- Criar teste de rota Bluetooth e garantir recuperação do perfil de música após chamada.
- Definir orçamento de frames, resolução, VRAM e temperatura para visão.
- Persistir mapa AR apenas mediante opt-in, criptografia, limite de armazenamento e botão de limpar.

### Fase D — biblioteca e recuperação de conhecimento

- Reportar formato detectado, estratégia de extração, páginas/partes ignoradas e confiança.
- Criar fixtures pequenas e seguras por formato; não executar conteúdo importado.
- Implementar índice com origem/citação interna verificável e remoção consistente do texto derivado.
- Distinguir metadado, OCR, transcrição e extração completa na interface.

### Fase E — evolução responsável

- Mostrar diferença entre melhoria proposta, experimento, candidato e release instalado.
- Exigir baseline/holdout, métricas de qualidade, latência, VRAM e energia.
- Interromper se segurança, qualidade ou limites de recursos piorarem.
- Preservar aprovação explícita para alterar runtime, instalar timer, treinar ou publicar.

## Como reportar um defeito

Inclua: commit/versão, sistema e versão do app, recurso, pré-requisitos, passos mínimos, esperado, observado, log sanitizado e frequência de reprodução. Remova antes tokens, emails pessoais, caminhos de usuário, URL de câmera, endereço IP, imagens privadas e conteúdo de conversa. Vulnerabilidades devem seguir o canal privado de `SECURITY.md`.

## Fatos do repositório que não devem ser confundidos com lacunas

- O projeto **tem** diretórios organizados `src/`, `tests/`, `scripts/` e módulos Android/Wear; logo, a afirmação de que não existe estrutura de código/testes é incorreta.
- Há 37 arquivos `tests/test_*.py` com testes `unittest`, mais scripts para suíte unitária e integração. Isso não fornece, por si só, um percentual de cobertura.
- A falta real é a ausência de workflow GitHub Actions/CI e de uma medição de coverage publicada. Sem execução, não se deve afirmar que a suíte passa ou que a cobertura é zero.
- O README já tem instalação rápida e requisitos; esta documentação acrescenta uso detalhado e exemplos. Ainda pode melhorar com screenshots e vídeos de fluxos reais.
- O título, pacote e URL usam consistentemente o nome “Vladmir”. O texto recebido não demonstra que seja erro: só o mantenedor pode dizer se o nome foi intencional ou se a marca desejada era “Vladimir”.
- A licença MIT padrão é coerente com o objetivo de publicar Vladmir como open source; “genérica” não é defeito técnico. A licença inclui o texto legal completo e o README explica o que ela permite. Componentes de terceiros mantêm avisos próprios.
- Ausência de arquivo de governança era real e foi corrigida nesta revisão com guia de contribuição, código de conduta e modelos para issue/PR.
- A alegação sobre marketing em Reddit não pode ser confirmada pelos arquivos do repositório e não é evidência de estado técnico.

## Critério de conclusão recomendado

Marque uma correção como concluída apenas quando houver evidência no mesmo nível do problema: leitura estática comprova fluxo no código; teste de unidade valida função isolada; integração valida serviços reais; ensaio físico valida câmera, áudio, Bluetooth ou sensores. Informe limites do ensaio e não transforme mock/fixture em prova de funcionamento do dispositivo.
