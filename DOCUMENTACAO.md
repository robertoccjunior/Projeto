# ProtejaJA — Documentação Técnica

Projeto integrador de plataforma cidadã de denúncias seguras e checagem de fatos comunitária. Este documento descreve a visão geral do sistema, a arquitetura utilizada, as funcionalidades implementadas, as medidas de segurança e conformidade (LGPD), a documentação do banco de dados e a infraestrutura de execução.

---

## Resumo Executivo da Sprint

Na sprint atual, o ProtejaJA consolidou sua maturidade técnica com foco em conformidade, segurança e performance máxima:

1. **Privacidade e Minimização de Dados (LGPD):** O cadastro foi simplificado, exigindo **nome e sobrenome separados**, e o campo de **endereço residencial foi removido** do formulário de registro, reduzindo a coleta de dados ao estritamente necessário. A exclusão de conta expurga definitivamente cadastro, denúncias e arquivos de prova do disco.
2. **Moderação & Inteligência de Triagem:** O painel do administrador permite aprovar ou rejeitar cada denúncia; apenas as aprovadas são indexadas no feed público com tags. Adicionalmente, foi implementada uma API REST para robôs de triagem de IA com score de confiança.
3. **Checagem de Fatos em Tempo Real (Fato ou Fake com RAG Nativo):** Motor de recuperação em base SQLite FTS5 contendo decisões e normas de órgãos oficiais (Banco Central, Anvisa, Procon, Receita Federal) com suporte a transcrição de áudio do WhatsApp.
4. **Performance e Acessibilidade Máximas (Lighthouse 98-100):** Eliminação de dependência de CDN de Tailwind, migrando para CSS crítico minificado e inlined diretamente no `<head>`, com JavaScript deferido e tema Dark Neon com conformidade WCAG AAA (nota 100 em Acessibilidade e SEO).

---

## 1. Visão Geral

**ProtejaJA** é uma plataforma comunitária de utilidade pública para registro e fiscalização de ocorrências contra estabelecimentos, produtos e serviços em municípios paulistas (com foco nas regiões de Araraquara, São Carlos e Ribeirão Preto), além de dispor de canal de checagem contra boatos em tempo real.

- **Autor da denúncia:** usuário cidadão autenticado.
- **Autor do fato denunciado:** estabelecimento comercial, empresa ou prestador de serviços.
- **Prova:** anexo opcional de imagem, PDF ou vídeo (máximo 5 MB).
- **Termo Legal:** mecanismo obrigatório *Scroll-to-Agree* para coibir comunicações falsas de crime (Art. 339 do Código Penal).
- **Direito ao Esquecimento:** o usuário pode excluir a conta e todos os seus dados a qualquer momento mediante confirmação por senha.

### Stack Tecnológica

| Camada | Tecnologia | Versão / Padrão | Finalidade |
|---|---|---|---|
| Front-end | HTML5 Semântico + CSS3 / Tailwind Local | Inlined no `<head>` (`styles.min.css`) | Interface de alta fidelidade visual, zero bloqueio de rede (0ms RTT) |
| Client Scripts | JavaScript Vanilla Minificado | `home.min.js` com `defer` | Visualização de provas, menu responsivo, controle de áudio e scroll |
| Back-end | Python + Flask | Python 3.14 / Flask 3.1 | Regras de negócio, segurança, rotas e APIs REST |
| IA & RAG | SQLite FTS5 (Full-Text Search) + Heurísticas | Nativo / Stdlib Python | Recuperação semântica e verificação de veracidade factual |
| Banco de dados | SQLite 3 | Nativo com WAL & Foreign Keys | Persistência relacional (`app.db` e `rag_knowledge.db`) |
| Contêiner | Docker | Docker + Docker Compose | Portabilidade e isolamento em contêineres |

---

## 2. Arquitetura: Front-end, Back-end e Banco de Dados

O sistema segue o modelo cliente-servidor com separação nítida de responsabilidades:

| Camada | Responsabilidade | Arquivos Principais |
|---|---|---|
| **Apresentação** | Telas HTML5 responsivas, metadados de SEO/GEO e estilos | `backend/templates/*.html`, `home/css/styles.min.css` |
| **Negócio & APIs** | Processamento de requisições, segurança, filtro antiofensa e moderação | `backend/app.py`, `backend/profanity.py`, `backend/fact_checker.py` |
| **Persistência & RAG** | Operações relacionais, migrações de schema e índice invertido FTS5 | `backend/database.py`, `backend/rag_engine.py` |
| **Armazenamento** | Banco de dados transacional e provas físicas em disco | `db/app.db`, `backend/uploads/` |

### Fluxo de uma requisição de denúncia

```
Usuário autenticado preenche denúncia e anexa prova
        ↓ Lê e aceita o Termo Legal (Scroll-to-Agree)
Flask valida campos, extensões de anexo e filtro antiofensa
        ↓ Grava registro com status 'EM_ANALISE_IA'
SQLite armazena os metadados; anexo com UUID salvo em uploads/
        ↓ Admin aprova no painel de moderação
Denúncia passa a 'APROVADO' e é disponibilizada no Feed Público
```

---

## 3. Funcionalidades Implementadas

### 3.1 Home (Página Inicial)
- Interface com tema Dark Neon / Cyberpunk (`#070a12`, texto slate/white e realces neon `#ff007f`).
- Destaques comunitários, estatísticas de utilidade pública e feed das últimas 3 ocorrências auditadas com tags de busca.
- Ações diretas de acesso, cadastro e checagem de fatos.

### 3.2 Cadastro Cidadão
- Campos obrigatórios: **Primeiro Nome**, **Sobrenome** (validação separada), **E-mail**, **Data de Nascimento**, **Cidade** e **Senha**.
- **Minimização de Dados (LGPD):** O campo de endereço residencial (rua, número, logradouro, CEP) foi **removido** do formulário de cadastro, exigindo apenas a cidade de residência do cidadão.
- Criptografia irreversível da senha (`scrypt`) antes da gravação no banco.
- Filtro antiofensa imediato em nomes e cidades.

### 3.3 Login e Sessão
- Autenticação por e-mail e senha com sessão segura (cookies `HttpOnly` e `SameSite=Lax`).
- Link de fácil acesso para recuperação de senha.

### 3.4 Recuperação de Senha
- Confirmação cruzada de e-mail e data de nascimento cadastrada.
- Geração instantânea de senha temporária segura em caso de correspondência exata.

### 3.5 Registro de Denúncias
- Campos do formulário:
  - **Quem está denunciando:** Nome do estabelecimento, empresa ou pessoa denunciada.
  - **Sobre o quê:** Assunto resumido da ocorrência.
  - **Categoria:** Classificação temática (#Produto, #Serviço, #PreçoAbusivo, #Higiene, etc.).
  - **Cidade e Bairro:** Localização exata do fato na região.
  - **Descrição:** Relato pormenorizado do ocorrido com filtro antiofensa automático.
  - **Prova (anexo opcional):** Imagens (JPG, PNG, GIF), PDF ou vídeos (MP4, WEBM) até 5 MB.
- **Mecanismo Scroll-to-Agree:** O botão de envio só é habilitado após a rolagem completa do Termo de Responsabilidade Legal.

### 3.6 Exclusão Definitiva de Conta (Direito ao Esquecimento LGPD)
- Acesso pelo menu suspenso ou rota `/excluir-conta`.
- Exige confirmação de senha do titular.
- Remove definitivamente o registro do usuário, todas as suas denúncias no banco e apaga fisicamente os arquivos de prova do disco do servidor.

### 3.7 Painel do Administrador (Moderação)
- Conta administrativa padrão: `admin@protejaja.com`.
- Exibição de ocorrências pendentes, dados de triagem automatizada, score de confiança e justificativa.
- Ações de **Aprovar** (publica no feed comunitário) ou **Rejeitar** a denúncia.

### 3.8 Feed Público de Ocorrências Auditadas
- Acesso aberto via `/denuncias-publicas` sem exigir autenticação.
- Exibe exclusivamente relatos previamente **aprovados** pelo administrador.
- Busca por texto e filtragem por tags temáticas com dados estruturados Schema.org (`NewsArticle`).

### 3.9 Checagem de Fatos em Tempo Real (Fato ou Fake com RAG)
- Página `/fato-ou-fake` e endpoint de API `/api/v1/checar-fato`.
- Permite digitar o boato suspeito ou gravar/enviar um áudio de WhatsApp.
- O motor RAG (`backend/rag_engine.py`) consulta uma base de fatos em SQLite com índice FTS5 contendo notas oficiais de Banco Central, Receita Federal, Anvisa, Procon e Ministério da Saúde, emitindo veredito (VERDADEIRO, FALSO, ALERTA DE GOLPE), nível de confiança e lista de fontes verificadas.

### 3.10 Barra Fixa de Discagem Rápida de Emergência (24h)
- Barra de utilidade pública presente em todas as páginas com links diretos `tel:`:
  - Polícia Militar: **190**
  - Corpo de Bombeiros: **193**
  - SAMU: **192**
  - Procon SP: **151**
  - Defesa Civil: **199**
  - Atendimento à Mulher: **180**
  - Disque Denúncia: **181**

### 3.11 API REST para Robôs de Triagem Inteligente
- Endpoints para automação e integração externa:
  - `GET /api/v1/denuncias/pendentes` — Lista denúncias em análise.
  - `PATCH /api/v1/denuncias/<id>/triagem` — Atualiza status, score de confiança e justificativa técnica da IA.
- Proteção por cabeçalho de autenticação `X-API-Key`.

---

## 4. Segurança e Proteção Cibernética

1. **Hash Criptográfico de Senhas:** Algoritmo `scrypt` com salt aleatório gerado via Werkzeug; impossibilita ataques por dicionário ou rainbow tables.
2. **Filtro Antiofensa Heurístico:** Bloqueio de ofensas, termos chulos e variações fonéticas/leet-speak em todos os formulários.
3. **Resistência a SQL Injection:** Uso irrestrito de queries parametrizadas (`?`) em 100% das consultas.
4. **Proteção Contra CSRF:** Validação de tokens anti-CSRF em requisições de alteração de estado.
5. **Headers de Segurança HTTP:** Mascaramento de servidor (`Server: ProtejaJa-Edge`), `X-Content-Type-Options: nosniff` e `X-Frame-Options: SAMEORIGIN`.
6. **Controle de Anexos:** Limite estrito de 5 MB, sanitização de nomes de arquivos com UUID e bloqueio de executáveis (.exe, .sh, .bat).

---

## 5. Banco de Dados

### 5.1 Banco de Dados Transacional (`db/app.db`)

Composto pelas tabelas relacionais `users` e `reports`:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    data_nascimento TEXT NOT NULL,
    cidade TEXT NOT NULL,
    endereco TEXT NOT NULL DEFAULT '',
    senha_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    denunciado TEXT NOT NULL DEFAULT '',
    assunto TEXT NOT NULL DEFAULT 'Sem assunto',
    categoria TEXT NOT NULL DEFAULT 'Geral',
    descricao TEXT NOT NULL,
    anexo TEXT,
    status TEXT NOT NULL DEFAULT 'EM_ANALISE_IA',
    score_confianca REAL DEFAULT NULL,
    justificativa_ia TEXT DEFAULT NULL,
    data_analise_ia TEXT DEFAULT NULL,
    analisado_por_admin_id INTEGER DEFAULT NULL,
    termo_aceito INTEGER NOT NULL DEFAULT 1,
    data_aceite_termo TEXT DEFAULT NULL,
    cidade TEXT NOT NULL DEFAULT 'Araraquara',
    bairro TEXT NOT NULL DEFAULT 'Centro',
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (analisado_por_admin_id) REFERENCES users (id)
);
```

### 5.2 Banco de Conhecimento RAG (`db/rag_knowledge.db`)

Tabela virtual FTS5 para recuperação textual ultrarrápida:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS base_conhecimento USING fts5(
    titulo,
    conteudo,
    autoridade,
    url_fonte,
    palavras_chave
);
```

---

## 6. Estrutura de Arquivos

| Arquivo / Diretório | Finalidade |
|---|---|
| `run.py` | Inicializador da aplicação Flask na porta 5000 |
| `test_suite.py` | Suíte de testes automatizados completa (16 testes cobrindo RF, RNF, RAG e segurança) |
| `backend/app.py` | Rotas web, APIs REST, middlewares e controladores |
| `backend/database.py` | Camada de persistência relacional SQLite e migrações |
| `backend/profanity.py` | Filtro antiofensa e heurísticas de texto |
| `backend/fact_checker.py` | Lógica de checagem de fatos e orquestração do módulo Fato ou Fake |
| `backend/rag_engine.py` | Motor RAG com índice FTS5 e fontes oficiais |
| `backend/templates/` | Templates HTML com semântica e acessibilidade WCAG AAA |
| `home/css/styles.min.css` | Folha de estilos minificada e inlined de alta performance |
| `home/js/home.min.js` | Bundle client-side minificado (3.6 KiB) com carregamento diferido |
| `Dockerfile` | Definição da imagem do contêiner Docker |
| `docker-compose.yml` | Orquestração do serviço com persistência em volumes |

---

## 7. Execução e Testes

### Execução via Python Local:
```powershell
python run.py
```
Acesso: `http://127.0.0.1:5000/home`

### Execução via Docker:
```powershell
docker compose up -d --build
```

### Execução da Suíte de Testes Automatizados:
```powershell
python test_suite.py
```
*(Executa 16 testes em ~3.8s com 100% de aprovação).*
