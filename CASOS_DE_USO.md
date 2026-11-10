# CASOS DE USO — ProtejaJA

**Projeto Integrador · Flask + SQLite + Tailwind CSS (Inlined) + RAG**

## 1. Diagrama (visão geral)

```
            ┌──────────────────┐
            │    VISITANTE     │   (não logado)
            └──────────────────┘
                 │
                 │  UC01 Cadastrar-se (sem exigência de endereço)
                 │  UC02 Entrar (login)
                 │  UC03 Recuperar senha
                 │  UC09 Checar fatos com áudio/RAG (Fato ou Fake)
                 │  UC11 Consultar feed comunitário com tags
                 │  UC14 Acessar telefones de emergência 24h
                 ▼
        ┌──────────────────────┐
        │       ProtejaJA      │
        │  Sistema de Denúncias │
        └──────────────────────┘
                 ▲
                 │
            ┌──────────────────┐
            │     USUÁRIO      │   (logado)
            └──────────────────┘
                 │
                 │  UC04 Enviar denúncia com cidade/bairro
                 │  UC05 Anexar prova (até 5 MB)
                 │  UC06 Ver minhas denúncias
                 │  UC07 Ver detalhes de uma denúncia
                 │  UC08 Sair (logout)
                 │  UC12 Excluir conta e expurgar dados (LGPD)
                 │  UC13 Ler e aceitar Termo Legal (Scroll-to-Agree)
                 ▼
            ┌──────────────────┐
            │  ADMINISTRADOR   │   (painel admin)
            └──────────────────┘
                 │
                 │  UC10 Moderar denúncias (aprovar ou rejeitar)
                 ▼
```

---

## 2. Tabela dos Casos de Uso

| Código | Caso de uso | Ator principal | Objetivo |
|---|---|---|---|
| **UC01** | Cadastrar-se | Visitante | Criar conta com nome, sobrenome, e-mail, data de nascimento, cidade e senha (sem exigir endereço residencial) |
| **UC02** | Entrar | Visitante | Acessar a conta com e-mail e senha com sessão segura |
| **UC03** | Recuperar senha | Visitante | Receber senha temporária informando e-mail + data de nascimento |
| **UC04** | Enviar denúncia | Usuário | Registrar quem está denunciando, o quê, categoria, cidade, bairro e descrição |
| **UC05** | Anexar prova | Usuário | Enviar imagem/PDF/vídeo (máx. 5 MB) junto à denúncia |
| **UC06** | Ver minhas denúncias | Usuário | Listar apenas as denúncias da própria conta em painel privativo |
| **UC07** | Ver detalhes de uma denúncia | Usuário | Abrir uma denúncia e ver a prova anexada e parecer de moderação |
| **UC08** | Sair | Usuário | Encerrar a sessão com segurança |
| **UC09** | Checagem de Fatos (Fato ou Fake) | Visitante / Usuário | Digitar boato ou enviar áudio de WhatsApp para verificação com motor RAG nativo |
| **UC10** | Moderar denúncias | Administrador | Analisar ocorrências no painel admin e aprovar para publicação ou rejeitar |
| **UC11** | Consultar feed público de denúncias | Visitante | Navegar pelo blog comunitário de ocorrências auditadas com filtros por tags |
| **UC12** | Excluir conta e dados (LGPD) | Usuário | Excluir definitivamente cadastro, denúncias e apagar fotos do disco com senha |
| **UC13** | Aceitar Termo Legal (Scroll-to-Agree) | Usuário | Rolar integralmente o contrato de responsabilidade para liberar o envio da denúncia |
| **UC14** | Discagem de emergência 24h | Visitante / Usuário | Acessar com 1 toque links diretos para 190, 193, 192, 151, 199, 180 e 181 |

---

## 3. Casos de uso em detalhe

### UC01 — Cadastrar-se (Minimização de Dados LGPD)

1. Visitante clica em **Cadastrar**.
2. Preenche primeiro nome, sobrenome, e-mail, data de nascimento, seleciona a cidade do estado de SP e cria uma senha forte (mínimo 6 caracteres).
3. O sistema valida que nome e sobrenome não estão vazios e aplica o filtro antiofensa.
4. **Nota de conformidade:** O endereço residencial não é solicitado, protegendo a privacidade física do cidadão.
5. Sistema grava a senha com hash `scrypt` e redireciona para o login com mensagem de sucesso.

### UC04 — Enviar denúncia

1. Usuário autenticado clica em **Cadastre sua Denúncia**.
2. Informa **quem está denunciando** (ex.: Hipermercado).
3. Informa **sobre o quê** (ex.: produto vencido).
4. Seleciona a **categoria** (produto, serviço, local...).
5. Seleciona a **cidade** e digita o **bairro** da ocorrência.
6. Escreve a **descrição** (filtro antiofensa valida o texto em tempo real).
7. (Opcional) **anexa a prova** (máximo 5 MB).
8. Rola o Termo de Responsabilidade até o fim (*Scroll-to-Agree*) e marca o checkbox de ciência legal.
9. Clica em **Enviar denúncia**.
10. Ocorrência é registrada com status `EM_ANALISE_IA` e enviada à moderação.

### UC09 — Checagem de Fatos com RAG (Fato ou Fake)

1. Usuário acessa `/fato-ou-fake`.
2. Grava um áudio pelo microfone, anexa um arquivo `.ogg`/`.mp3` de WhatsApp ou digita a notícia.
3. Clica em **Checar Veracidade**.
4. O sistema consulta a base oficial em SQLite FTS5 e retorna o veredito (Verdadeiro, Falso, Alerta de Golpe) acompanhado de evidências e links de fontes oficiais.

### UC12 — Excluir conta definitivamente (LGPD)

1. Usuário acessa `/excluir-conta`.
2. O sistema exibe alerta informando que a operação é irreversível.
3. Usuário digita sua senha para confirmação.
4. O sistema valida a senha, remove o usuário do banco, apaga todas as suas denúncias e remove permanentemente todos os arquivos de prova do diretório físico `uploads/`.

---

## 4. Fontes dos Casos de Uso

Rotas implementadas no back-end (`backend/app.py`):
- `/cadastro`, `/login`, `/recuperar`, `/denuncias`, `/logout`, `/fato-ou-fake`, `/admin`, `/denuncias-publicas`, `/excluir-conta`, `/api/v1/checar-fato`.
