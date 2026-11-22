# JARVIS OS v4.1

Este repositório publica o arquivo **`JARVIS_OS_V4_1.zip`**, que é a versão usada no serviço Render. O Dockerfile extrai esse arquivo durante o build. A pasta `JARVIS/` dentro do ZIP contém a aplicação Python, a interface web e os scripts de inicialização para Windows, Linux/macOS e Termux.

## Serviço publicado

- URL: https://jarvis-os-fgustakimiteste.onrender.com
- Plataforma: Render Web Service (Docker)
- Branch: `main`
- Região: Frankfurt
- Porta: fornecida pelo Render por meio da variável `PORT`
- Arquivo publicado: `JARVIS_OS_V4_1.zip`

## O que a v4.1 contém

- Interface web responsiva para conversar com o assistente.
- Integração com Google Gemini pelo SDK `google-genai`.
- Histórico e memórias SQLite.
- Pesquisa web pública e leitura de páginas públicas com proteção contra destinos internos.
- Ferramentas locais e scripts de inicialização para PC e Android via Termux.
- Descoberta e diagnóstico da rede local na instalação executada no próprio computador.

## Diferenças entre a instalação local e o serviço público

A versão original foi concebida principalmente para rodar no computador do usuário e permitir que o Android acesse esse computador pela mesma rede Wi-Fi. No serviço hospedado, o JARVIS roda no servidor Render, não no celular ou na rede doméstica do visitante.

Por isso, a implantação pública aplica um adaptador no build Docker que:

- Cria uma sessão aleatória por navegador, em cookie `HttpOnly`, `Secure` e `SameSite=Lax`.
- Separa histórico e memórias em bancos SQLite distintos por sessão, para não compartilhar conversas entre visitantes.
- Desativa o scanner de rede LAN e a abertura do painel do roteador na instância hospedada. Essas ferramentas funcionam apenas na instalação local, no computador que o usuário controla.
- Evita tentar abrir aplicações ou janelas no computador servidor quando o usuário pede para abrir um site.

Essas adaptações são aplicadas somente à imagem Docker pública. O ZIP original permanece no repositório sem ser reescrito.

## Ativar as respostas de IA

A chave do Gemini não é incluída no código nem no ZIP. Para ativar respostas generativas:

1. Abra o painel do serviço Render.
2. Entre em **Environment**.
3. Adicione `GEMINI_API_KEY` com sua chave do Google AI Studio.
4. Salve e aguarde o redeploy.

A chave deve ficar apenas nas variáveis privadas do Render. Não a envie por chat nem faça commit dela no GitHub. Sem a chave, a interface e as funções locais disponíveis continuam abrindo, mas as respostas generativas do Gemini não funcionam.

## Persistência e disponibilidade

O serviço está no plano gratuito do Render. Esse plano pode suspender a instância após inatividade. O armazenamento de arquivos do contêiner é efêmero por padrão; portanto, histórico e memórias criados no servidor podem ser perdidos em reinicializações ou novos deploys. Para uso contínuo, configure armazenamento persistente e backups antes de guardar dados importantes.

## Android

A v4.1 **não é um APK Android independente**. O Android pode acessar a interface pelo navegador. Para usar o scanner e as ferramentas LAN na sua própria rede, rode o backend no seu PC ou instale-o localmente pelo Termux, conforme as instruções em `JARVIS/README.md` dentro do ZIP.

## Segurança

Não coloque chaves de API, tokens, arquivos `.env` ou dados pessoais no repositório público. Use variáveis privadas no Render. O bloqueio de dispositivos no roteador não está implementado universalmente: a versão original informa essa limitação e não finge desconectar aparelhos.
