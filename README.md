# JARVIS OS — implantação da interface original

O arquivo **`JARVIS-OS-V.2-main.zip`** permanece como fonte original do aplicativo. Ele contém duas aplicações distintas:

- `ui.py` + `main.py`: interface desktop original PyQt6, com Mission Control, painéis de sistema/agentes, HUD central e Command Rail.
- `web/`: cliente web Next.js separado, documentado no README original como hosted web application.

## Interface desktop original no navegador

A interface principal PyQt6 pode ser visualizada por uma sessão de desktop remoto protegida por autenticação. O serviço `jarvis-desktop` extrai o ZIP sem editar seus arquivos, inicia `main.py` em Xvfb/Openbox e transmite a janela original por noVNC.

- Endereço: fornecido pelo serviço `jarvis-desktop` no Render.
- Login HTTP: `jarvis`
- Senha: variável privada `JARVIS_REMOTE_PASSWORD` no Render.
- Health check: `/healthz`

O desktop remoto é uma única sessão compartilhada, não uma sessão por visitante. O app roda no contêiner, não no computador do navegador. Assim, ações locais atuam apenas no ambiente isolado do contêiner. O noVNC não encaminha o microfone físico do navegador ao PortAudio; esta publicação serve para exibir e interagir com a UI original e usar os recursos que não dependam do hardware do PC local.

## Cliente web original

O cliente `web/` do ZIP segue preservado e continua disponível no serviço web separado. Ele é a aplicação web hospedada prevista pelo repositório; não é uma conversão da janela desktop PyQt6.

## Fonte e alterações

O ZIP original não é recomposto nem modificado. `Dockerfile.desktop` e `deploy/remote-desktop/` são apenas arquivos adicionais de infraestrutura para executar a interface PyQt6 original em uma sessão gráfica virtual e protegida.
