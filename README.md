# 🛡️ ProtejaJÁ — Plataforma Cidadã de Denúncias e Checagem de Fatos

**Projeto Integrador** de utilidade pública para registro seguro de ocorrências contra estabelecimentos, produtos e serviços (com foco regional no interior paulista: Araraquara, São Carlos, Ribeirão Preto e região), aliado a um canal de verificação de boatos em tempo real (**Fato ou Fake**).

---

## Principais Funcionalidades

- **Registro de Denúncias com Provas:** Envio de relatos categorizados (`#Produto`, `#Serviço`, `#PreçoAbusivo`, `#Higiene`, etc.) com localização (cidade/bairro), anexo de evidências (imagens, PDF ou vídeo até 5 MB) e mecanismo obrigatório *Scroll-to-Agree* do Termo de Responsabilidade Legal (Art. 339 do Código Penal).
- **Moderação e Feed Público Auditado:** Painel administrativo para aprovação ou rejeição de ocorrências e integração via API REST para triagem automatizada com score de confiança. Apenas relatos aprovados vão para o feed comunitário público (`/denuncias-publicas`).
- **Fato ou Fake (Checagem em Tempo Real):** Verificação instantânea de boatos por texto ou áudio de WhatsApp, consultando base de conhecimento indexada (SQLite FTS5) e fontes oficiais (Banco Central, Receita Federal, Anvisa, Procon, Ministério da Saúde e portais de checagem).
- **Privacidade e Conformidade LGPD:**
  - *Minimização de dados:* Cadastro exige apenas nome, sobrenome, e-mail, data de nascimento e cidade (sem coleta de endereço residencial).
  - *Direito ao Esquecimento:* Exclusão definitiva de conta (`/excluir-conta`) mediante senha, expurgando usuário, denúncias no banco e arquivos físicos de prova em `backend/uploads/`.
- **Segurança & Filtro Antiofensa:** Hash criptográfico `scrypt`, queries 100% parametrizadas contra SQL Injection, proteção CSRF, cabeçalhos HTTP de segurança e bloqueio heurístico de palavras ofensivas/leet-speak.
- **Alta Performance & Acessibilidade (WCAG AAA):** Interface *Dark Neon / Cyberpunk* com CSS crítico minificado inlined no `<head>`, compressão Gzip nativa e barra fixa 24h com discagem rápida de emergência (`190`, `193`, `192`, `151`, `199`, `180`, `181`).

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Descrição |
|---|---|---|
| **Back-end** | Python 3.12+ / Flask 3.x | Rotas web, autenticação, moderação, segurança e APIs REST |
| **Banco de Dados** | SQLite 3 (Relacional + FTS5) | Persistência transacional (`db/app.db`) e base textual indexada (`db/rag_knowledge.db`) |
| **Front-end** | HTML5 Semântico + CSS3 / JS Vanilla | Templates Jinja2 acessíveis, CSS minificado (`styles.min.css`) e JS deferido (`home.min.js`) |
| **Infraestrutura** | Docker & Docker Compose | Empacotamento reproduzível com volumes persistentes |
| **Qualidade** | `unittest` (`test_suite.py`) | 19 testes automatizados cobrindo RF, RNF, segurança, LGPD e checagem de fatos |

---

## Estrutura do Projeto

```text
protejaja/
├── backend/
│   ├── templates/           # Telas HTML5 (home, login, cadastro, denuncias, admin, fato_ou_fake...)
│   ├── uploads/             # Armazenamento físico seguro de anexos de provas
│   ├── app.py               # Aplicação Flask, rotas, middlewares HTTP e endpoints REST
│   ├── database.py          # Camada de persistência SQLite, migrações e queries parametrizadas
│   ├── fact_checker.py      # Orquestrador do módulo Fato ou Fake e transcrição de áudio
│   ├── agentic_checker.py   # Pipeline de verificação web em fontes de autoridade
│   ├── rag_engine.py        # Motor de busca textual em SQLite FTS5 com fatos oficiais
│   └── profanity.py         # Filtro antiofensa e sanitização de texto
├── db/
│   ├── app.db               # Banco de dados relacional (usuários e denúncias)
│   └── rag_knowledge.db     # Base de conhecimento oficial indexada via FTS5
├── home/
│   ├── css/                 # Estilos CSS (styles.css e styles.min.css)
│   ├── js/                  # Scripts client-side (home.src.js, home.js e home.min.js)
│   └── index.html           # Landing estática de referência
├── wireframes/
│   └── wireframes.html      # Protótipos visuais navegáveis das telas
├── run.py                   # Ponto de entrada da aplicação (porta 5000)
├── test_suite.py            # Suíte completa de testes automatizados (19 testes)
├── requirements.txt         # Dependências Python do projeto
├── Dockerfile               # Imagem Docker Python 3.12-slim
├── docker-compose.yml       # Orquestração do contêiner e volumes
├── DOCUMENTACAO.md          # Documentação técnica detalhada e arquitetura
├── REQUISITOS.md            # Especificação de Requisitos Funcionais (RF) e Não Funcionais (RNF)
├── CASOS_DE_USO.md          # Diagrama e detalhamento dos Casos de Uso (UC01 a UC14)
└── WIREFRAME.md             # Documentação dos wireframes e manipulação de imagens
```

---

## Como Executar o Projeto

### Opção 1: Execução Local com Python

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Inicie o servidor:**
   ```bash
   python run.py
   ```

3. **Acesse no navegador:**
   - Aplicação: `http://127.0.0.1:5000/home`
   - Fato ou Fake: `http://127.0.0.1:5000/fato-ou-fake`
   - Feed Público: `http://127.0.0.1:5000/denuncias-publicas`
   - Painel Admin: `http://127.0.0.1:5000/admin`

### Opção 2: Execução com Docker

```bash
docker compose up -d --build
```
A aplicação ficará disponível em `http://localhost:5000/home` com persistência automática para `db/` e `backend/uploads/`.

---

## Credenciais Padrão (Ambiente de Desenvolvimento/Avaliação)

O banco de dados inicializa automaticamente a conta de moderação:

- **E-mail do Administrador:** `admin@protejaja.com`
- **Senha:** `admin123`
- **Chave padrão da API de Triagem (`X-API-Key`):** `protejaja-bot-secret-key-2026`

*(Você também pode criar novas contas de cidadão livremente pela rota `/cadastro`).*

---

## Executando os Testes

Para rodar os testes (Requisitos Funcionais, Não Funcionais, LGPD, Acessibilidade e Fato ou Fake):

```bash
python test_suite.py
```

---

## Documentação Complementar

 [**Documentação Técnica Completa (`DOCUMENTACAO.md`)**](./DOCUMENTACAO.md)
 [**Requisitos Funcionais e Não Funcionais (`REQUISITOS.md`)**](./REQUISITOS.md)
 [**Casos de Uso (`CASOS_DE_USO.md`)**](./CASOS_DE_USO.md)
 [**Wireframes e Manipulação de Imagem (`WIREFRAME.md`)**](./WIREFRAME.md)
