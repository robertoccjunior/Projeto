# 🛡️ ProtejaJÁ — Plataforma Cidadã de Denúncias Seguras

**Projeto Integrador** de utilidade pública com **abrangência nacional (todos os 5.570 municípios do Brasil)** para registro seguro de ocorrências contra estabelecimentos, produtos e serviços, aliado a um **Portal de Notícias e Alertas**.

---

## Principais Funcionalidades

- **Registro de Denúncias com Provas e Autocomplete Nacional:** Envio de relatos categorizados com autocomplete otimizado de todos os municípios brasileiros (base IBGE, formato `Cidade - UF`), bairro, anexo de evidências (imagens, PDF ou vídeo até 5 MB) e aceite obrigatório do Termo de Responsabilidade Legal (Art. 299/340 do Código Penal).
- **Moderação e Feed Público Auditado:** Painel administrativo para aprovação ou rejeição de ocorrências. Apenas relatos aprovados vão para o feed comunitário público (`/denuncias-publicas`), com filtro por município nacional e palavras-chave.
- **Portal de Notícias e Alertas (`/noticias`):** Acompanhamento de notícias e alertas oficiais sobre golpes, impostos, dinheiro público e direitos do consumidor.
- **Privacidade e Maioridade:**
  - *Minimização de dados e 18+:* Cadastro exige apenas nome, sobrenome, e-mail, data de nascimento (com validação estrita de maioridade >= 18 anos) e município, com indicação explícita de campos obrigatórios (`* (obrigatório)`).
  - *Direito ao Esquecimento:* Exclusão definitiva de conta (`/excluir-conta`) mediante senha, expurgando usuário, denúncias no banco e arquivos físicos de prova em `backend/uploads/`.
- **Segurança & Filtro Antiofensa:** Hash criptográfico `scrypt`, queries 100% parametrizadas contra SQL Injection, proteção CSRF, cabeçalhos HTTP de segurança e bloqueio heurístico de palavras ofensivas/leet-speak.
- **Alta Performance & Acessibilidade (WCAG AAA):** Interface *Dark Neon / Cyberpunk* com CSS crítico minificado inlined no `<head>`, compressão Gzip nativa e barra fixa com discagem rápida de emergência e apoio (`190`, `193`, `192`, `151`, `199`, `180`, `181`).

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Descrição |
|---|---|---|
| **Back-end** | Python 3.12+ / Flask 3.x | Rotas web, autenticação, moderação e segurança |
| **Banco de Dados** | SQLite 3 (Relacional) | Persistência transacional (`db/app.db`) |
| **Front-end** | HTML5 Semântico + CSS3 / JS Vanilla | Templates Jinja2 acessíveis, CSS minificado (`styles.min.css`) e JS deferido (`home.min.js`) |
| **Infraestrutura** | Docker & Docker Compose | Empacotamento reproduzível com volumes persistentes |
| **Qualidade** | `unittest` (`test_suite.py`) | Suíte de testes automatizados cobrindo RF, RNF e segurança |

---

## Estrutura do Projeto

```text
protejaja/
├── .github/workflows/
│   └── deploy-eks.yml             # Pipeline de deploy para Kubernetes (EKS)
├── backend/
│   ├── data/
│   │   └── municipios.json        # Base oficial IBGE de municípios brasileiros (Cidade - UF)
│   ├── templates/                 # Telas HTML5 (home, login, cadastro, denuncias, denuncia_termo, admin, noticias, diferencial, excluir_conta, ver_denuncia...)
│   ├── uploads/                   # Armazenamento físico seguro de anexos de provas
│   ├── app.py                     # Aplicação Flask, rotas e middlewares HTTP
│   ├── database.py                # Camada de persistência SQLite, migrações e queries parametrizadas
│   ├── municipios.py              # Índice em memória e busca normalizada dos 5.570 municípios IBGE
│   ├── news_portal.py             # Agregador de notícias e alertas por categoria
│   └── profanity.py               # Filtro antiofensa e sanitização de texto
├── db/
│   └── app.db                     # Banco de dados relacional (usuários e denúncias)
├── home/
│   ├── css/                       # Estilos CSS (styles.css e styles.min.css)
│   └── js/                        # Scripts client-side (home.src.js, home.js, home.min.js e municipios-autocomplete.js)
├── k8s/
│   └── deployment.yaml            # Manifesto de deploy Kubernetes
├── iniciar_protejaja.bat          # Inicializador automático (instala Python 3.14 se necessário, cria .venv, instala dependências e abre o navegador)
├── run.py                         # Ponto de entrada da aplicação (porta 5000)
├── test_suite.py                  # Suíte completa de testes automatizados (20 testes)
├── requirements.txt               # Dependências Python do projeto
├── Dockerfile                     # Imagem Docker Python 3.12-slim
├── docker-compose.yml             # Orquestração do contêiner e volumes
├── DOCUMENTACAO.md                # Documentação técnica detalhada e arquitetura
├── REQUISITOS.md                  # Especificação de Requisitos Funcionais (RF) e Não Funcionais (RNF)
├── CASOS_DE_USO.md                # Diagrama e detalhamento dos Casos de Uso (UC01 a UC14)
└── WIREFRAME.md                   # Documentação dos wireframes e manipulação de imagens
```

---

## Como Executar o Projeto

### Opção 1: Execução Automática no Windows (Recomendada)

Dê um duplo clique no arquivo **`iniciar_protejaja.bat`**. Ele faz tudo automaticamente:
1. Verifica se o Python está instalado (caso não esteja, baixa e instala o **Python 3.14** automaticamente).
2. Cria o ambiente virtual (`.venv`) e instala as dependências de `requirements.txt`.
3. Inicia o servidor Flask e abre `http://127.0.0.1:5000/home` no navegador.

### Opção 2: Execução Manual com Python

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
   - Portal de Notícias: `http://127.0.0.1:5000/noticias`
   - Feed Público: `http://127.0.0.1:5000/denuncias-publicas`
   - Painel Admin: `http://127.0.0.1:5000/admin`

### Opção 3: Execução com Docker

```bash
docker compose up -d --build
```
A aplicação ficará disponível em `http://localhost:5000/home` com persistência automática para `db/` e `backend/uploads/`.

---

## Credenciais Padrão (Ambiente de Desenvolvimento/Avaliação)

O banco de dados inicializa automaticamente a conta de moderação:

- **E-mail do Administrador:** `admin@protejaja.com`
- **Senha:** `admin123`

*(Você também pode criar novas contas de cidadão livremente pela rota `/cadastro`).*

---

## Executando os Testes

Para rodar os testes (Requisitos Funcionais, Não Funcionais, Segurança e Acessibilidade):

```bash
python test_suite.py
```

---

## Documentação Complementar

 [**Documentação Técnica Completa (`DOCUMENTACAO.md`)**](./DOCUMENTACAO.md)
 [**Requisitos Funcionais e Não Funcionais (`REQUISITOS.md`)**](./REQUISITOS.md)
 [**Casos de Uso (`CASOS_DE_USO.md`)**](./CASOS_DE_USO.md)
 [**Wireframes e Manipulação de Imagem (`WIREFRAME.md`)**](./WIREFRAME.md)
