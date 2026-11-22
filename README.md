# JARVIS OS — versão publicada

Este repositório publica o pacote **`JARVIS-OS-V.2-main.zip`** enviado para a branch `main`. O pacote original é mantido intacto; os Dockerfiles o extraem durante o build e aplicam adaptações de hospedagem.

## Aplicação hospedada

- Interface web: https://jarvis-web-fgustakimiteste.onrender.com
- API: https://jarvis-os-fgustakimiteste.onrender.com
- Plataforma: Render
- Branch: `main`
- Região: Frankfurt
- A interface e a API são serviços separados.

A interface web Next.js usa a API FastAPI e o canal WebSocket. O backend hospeda contas individuais; cada usuário cria sua conta e conecta sua própria chave Gemini. As chaves são criptografadas antes de serem guardadas no banco.

## Verificação da chave Gemini Live

O backend não considera `models.list()` suficiente para declarar que um projeto tem ou não acesso ao Gemini Live. Ao salvar uma chave, ele tenta abrir uma conexão Live real, sem enviar áudio ou prompt. A seleção de modelo também usa o modelo configurado como fallback quando a listagem não informa os recursos Live; a autorização real é decidida pelo handshake WebSocket.

## Como o build usa o pacote

- `Dockerfile`: extrai o ZIP e inicia `api.server:app` com as migrações Alembic.
- `Dockerfile.web`: extrai o mesmo ZIP, instala as dependências de `web/` e compila a interface Next.js.
- `render_v2_patch.py`: aplica ajustes de hospedagem sem reescrever o ZIP original.

## Limitação atual do plano gratuito

Para manter a publicação sem adicionar cobrança, a API usa SQLite dentro do contêiner e limite de requisições em memória. O isolamento entre contas é mantido pela identidade autenticada de cada usuário, mas o armazenamento do contêiner gratuito é efêmero: contas, conversas e chaves criptografadas podem ser perdidas em reinicializações, suspensões ou novos deploys. Não guarde dados importantes nesta implantação até configurar PostgreSQL persistente e backups. Para várias instâncias, configure também Redis.

## Primeiro acesso

1. Abra a interface web.
2. Crie uma conta com e-mail e senha.
3. Na etapa de configuração, conecte sua chave Gemini do Google AI Studio.
4. Permita o microfone no navegador para usar a voz. O canal de texto também fica disponível.

Cada conta tem sua própria sessão e seus próprios dados. A autenticação é por conta, não por um token manual compartilhado entre visitantes.

## Ferramentas locais e ferramentas na nuvem

O pacote conserva o aplicativo desktop, agentes, automações, ferramentas e interface original dentro do ZIP. A interface pública usa a API hospedada e disponibiliza somente os recursos compatíveis com execução na nuvem. Funções que dependem do computador físico do usuário — por exemplo, controlar janelas, arquivos locais, microfone do sistema operacional ou dispositivos da rede doméstica — precisam ser executadas na instalação local e não podem ser executadas pelo servidor Render.

## Segurança

- Não coloque `.env`, chaves de API ou dados privados no GitHub.
- Cada usuário conecta sua própria chave Gemini na área autenticada.
- `JWT_SECRET` e `JARVIS_ENCRYPTION_KEY` ficam nas variáveis privadas do Render.
- A versão gratuita usa armazenamento efêmero; atualize para banco persistente antes de uso contínuo.
