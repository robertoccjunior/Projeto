# ProtejaJA — Documentação Técnica

Projeto integrador de plataforma cidadã de denúncias seguras e utilidade pública. Este documento descreve a visão geral do sistema, a arquitetura utilizada, as funcionalidades implementadas, as medidas de segurança, a documentação do banco de dados e a infraestrutura de execução.

---

## Resumo Executivo da Sprint

Na sprint atual, o ProtejaJA consolidou sua maturidade técnica com foco em segurança e performance máxima:

1. **Privacidade e Minimização de Dados:** O cadastro exige **nome e sobrenome separados**, e-mail, data de nascimento (18+ anos) e município, reduzindo a coleta de dados ao estritamente necessário. A exclusão de conta expurga definitivamente cadastro, denúncias e arquivos de prova do disco.
2. **Moderação & Feed Público:** O painel do administrador permite aprovar ou rejeitar cada denúncia; apenas as aprovadas são exibidas no feed público.
3. **Portal de Notícias e Alertas (`/noticias`):** Central informativa com notícias e alertas sobre golpes, impostos, dinheiro público e direitos do consumidor.
4. **Performance e Acessibilidade Máximas (Lighthouse 98-100):** Eliminação de dependência de CDN de Tailwind, migrando para CSS crítico minificado e inlined diretamente no `<head>`, com JavaScript deferido e tema Dark Neon com conformidade WCAG AAA (nota 100 em Acessibilidade e SEO).

---

## 1. Visão Geral

**ProtejaJA** é uma plataforma comunitária de utilidade pública com **abrangência nacional (todos os 5.570 municípios do Brasil)** para registro e fiscalização de ocorrências contra estabelecimentos, produtos e serviços.

- **Autor da denúncia:** usuário cidadão autenticado.
- **Autor do fato denunciado:** estabelecimento comercial, empresa ou prestador de serviços.
- **Prova:** anexo opcional de imagem, PDF ou vídeo (máximo 5 MB).
- **Termo Legal:** aceite obrigatório para coibir comunicações falsas de crime (Art. 339 do Código Penal).
- **Direito ao Esquecimento:** o usuário pode excluir a conta e todos os seus dados a qualquer momento mediante confirmação por senha.

### Stack Tecnológica

| Camada | Tecnologia | Versão / Padrão | Finalidade |
|---|---|---|---|
| Front-end | HTML5 Semântico + CSS3 / Tailwind Local | Inlined no `<head>` (`styles.min.css`) | Interface de alta fidelidade visual, zero bloqueio de rede (0ms RTT) |
| Client Scripts | JavaScript Vanilla Minificado | `home.min.js` com `defer` | Visualização de provas, menu responsivo, controle de áudio e scroll |
| Back-end | Python + Flask | Python 3.12+ / Flask 3.x | Regras de negócio, segurança e rotas web |
| Banco de dados | SQLite 3 | Nativo com WAL & Foreign Keys | Persistência relacional (`app.db`) |
| Contêiner | Docker | Docker + Docker Compose | Portabilidade e isolamento em contêineres |

---

## 2. Arquitetura: Front-end, Back-end e Banco de Dados

O sistema segue o modelo cliente-servidor com separação nítida de responsabilidades:

| Camada | Responsabilidade | Arquivos Principais |
|---|---|---|
| **Apresentação** | Telas HTML5 responsivas, metadados de SEO/GEO e estilos | `backend/templates/*.html`, `home/css/styles.min.css` |
| **Negócio** | Processamento de requisições, segurança, filtro antiofensa e moderação | `backend/app.py`, `backend/profanity.py` |
| **Persistência** | Operações relacionais e migrações de schema | `backend/database.py` |
| **Armazenamento** | Banco de dados transacional e provas físicas em disco | `db/app.db`, `backend/uploads/` |

### Fluxo de uma requisição de denúncia

```
Usuário autenticado preenche denúncia e anexa prova
        ↓ Lê e aceita o Termo Legal
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
- Destaques comunitários, estatísticas de utilidade pública e feed das últimas ocorrências auditadas.
- Ações diretas de acesso, cadastro e consulta de ocorrências.

### 3.2 Cadastro Cidadão
- Campos obrigatórios (marcados com `*` vermelho): **Primeiro Nome**, **Sobrenome** (validação separada), **E-mail**, **Data de Nascimento** (18+ anos), **Cidade**, **Senha** (mínimo 8 caracteres, com 1 maiúscula e 1 minúscula) e **Confirmar Senha**.
- Criptografia irreversível da senha (`scrypt`) antes da gravação no banco.
- Filtro antiofensa imediato em nomes e cidades.

### 3.3 Login e Sessão
- Autenticação por e-mail e senha com sessão segura (cookies `HttpOnly` e `SameSite=Lax`).

### 3.4 Registro de Denúncias
- Campos do formulário:
  - **Quem está denunciando:** Nome do estabelecimento, empresa ou pessoa denunciada.
  - **Sobre o quê:** Assunto resumido da ocorrência.
  - **Categoria:** Classificação temática (Produto, Serviço, Preço Abusivo, Higiene, etc.).
  - **Cidade e Bairro:** Localização exata do fato na região.
  - **Descrição:** Relato pormenorizado do ocorrido com filtro antiofensa automático.
  - **Prova (anexo opcional):** Imagens (JPG, PNG, GIF), PDF ou vídeos (MP4, WEBM) até 5 MB.
- **Termo Legal:** O envio exige leitura e aceite do Termo de Responsabilidade Legal.

### 3.6 Exclusão Definitiva de Conta (Direito ao Esquecimento)
- Acesso pelo menu suspenso ou rota `/excluir-conta`.
- Exige confirmação de senha do titular.
- Remove definitivamente o registro do usuário, todas as suas denúncias no banco e apaga fisicamente os arquivos de prova do disco do servidor.

### 3.7 Painel do Administrador (Moderação)
- Conta administrativa padrão: `admin@protejaja.com`.
- Exibição de ocorrências pendentes.
- Ações de **Aprovar** (publica no feed comunitário) ou **Rejeitar** a denúncia.

### 3.8 Feed Público de Ocorrências Auditadas
- Acesso aberto via `/denuncias-publicas` sem exigir autenticação.
- Exibe exclusivamente relatos previamente **aprovados** pelo administrador.
- Busca por texto, autocomplete nacional de municípios (`/api/municipios`) e filtragem por categoria com dados estruturados Schema.org (`NewsArticle`).

### 3.8 Portal de Notícias e Alertas
- Página `/noticias` com notícias e alertas filtrados por tema (golpes, impostos, consumidor).

### 3.9 Barra Fixa de Discagem Rápida de Emergência e Apoio
- Barra de utilidade pública presente em todas as páginas com links diretos `tel:`:
  - Polícia Militar: **190**
  - Corpo de Bombeiros: **193**
  - SAMU: **192**
  - Procon: **151** (horário comercial)
  - Defesa Civil: **199**
  - Atendimento à Mulher: **180**
  - Disque Denúncia: **181**

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

---

## 6. Estrutura de Arquivos

| Arquivo / Diretório | Finalidade |
|---|---|
| `iniciar_protejaja.bat` | Inicializador automático no Windows (instala Python/dependências e abre o navegador) |
| `run.py` | Inicializador da aplicação Flask na porta 5000 |
| `test_suite.py` | Suíte de testes automatizados completa cobrindo RF, RNF e segurança |
| `backend/app.py` | Rotas web, middlewares e controladores |
| `backend/database.py` | Camada de persistência relacional SQLite e migrações |
| `backend/profanity.py` | Filtro antiofensa e heurísticas de texto |
| `backend/news_portal.py` | Agregador de notícias e alertas por categoria |
| `backend/templates/` | Templates HTML com semântica e acessibilidade WCAG AAA |
| `home/css/styles.min.css` | Folha de estilos minificada e inlined de alta performance |
| `home/js/home.min.js` | Bundle client-side minificado (3.6 KiB) com carregamento diferido |
| `Dockerfile` | Definição da imagem do contêiner Docker |
| `docker-compose.yml` | Orquestração do serviço com persistência em volumes |

---

## 7. Execução e Testes

### Execução Automática no Windows:
Dê um duplo clique em `iniciar_protejaja.bat` (baixa/detecta o Python, instala `requirements.txt` e abre `http://127.0.0.1:5000/home`).

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
*(Executa 20 testes com 100% de aprovação).*
