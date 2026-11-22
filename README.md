# JARVIS OS

Repositório público de publicação do JARVIS OS v4.3. O código-fonte completo está empacotado em `Jarvis_OS_v4_3_Public_Ready.zip`; o `Dockerfile` da raiz extrai o pacote durante o build do Render e instala as dependências da aplicação.

## Publicação

- Plataforma: Render Web Service (Docker)
- Branch: `main`
- Health check: `/healthz`
- Porta: definida automaticamente por `PORT`
- Modo público: sessões anônimas separadas por navegador; recursos de controle do computador/rede do servidor desativados na instância compartilhada.

## Configuração privada

Configure somente no painel Environment do Render, nunca no GitHub:

- `OPENAI_API_KEY` e/ou `GEMINI_API_KEY` para habilitar os provedores de IA.
- `JARVIS_LEGAL_NAME`, `JARVIS_LEGAL_ADDRESS`, `JARVIS_PRIVACY_EMAIL` e, quando aplicável, `JARVIS_CNPJ` e `JARVIS_DPO_CONTACT`, usando dados reais do responsável.
- IDs de verificação/analytics apenas depois de configurar e validar o consentimento.

Nenhuma chave real está incluída neste repositório.

## Persistência e limites

A implantação gratuita do Render pode suspender por inatividade e usa armazenamento efêmero por padrão. Para guardar conversas, memórias e arquivos de forma confiável, configure disco persistente e backups ou migre para banco gerenciado/armazenamento de objetos antes de uso contínuo.

As páginas legais são modelos iniciais e precisam ser preenchidas com dados verdadeiros e revisadas juridicamente antes de uso comercial.
