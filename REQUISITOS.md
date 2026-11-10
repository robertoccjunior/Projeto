# ProtejaJA — Requisitos Funcionais e Não Funcionais

Este documento especifica os requisitos do sistema ProtejaJA, organizados em requisitos funcionais (o que o sistema faz) e requisitos não funcionais (como o sistema se comporta, qualidade e segurança).

---

## 1. Conceitos

| Tipo | Pergunta que responde | Exemplo |
|---|---|---|
| **Funcional** | O que o sistema faz? | Cadastrar, entrar, registrar denúncia, checar fatos |
| **Não funcional** | Como o sistema executa? | Senha com hash scrypt, carregamento < 25ms, acessibilidade WCAG AAA |

---

## 2. Requisitos Funcionais

| Código | Requisito Funcional | Local |
|---|---|---|
| RF01 | O sistema deve permitir cadastrar usuário com nome e sobrenome separados (ambos obrigatórios), e-mail, data de nascimento, cidade e senha (sem exigência de endereço residencial, respeitando a minimização de dados da LGPD). | Tela Cadastro |
| RF02 | O sistema deve criptografar a senha com algoritmo scrypt antes de armazená-la no banco. | Cadastro |
| RF03 | O sistema deve permitir o login com e-mail e senha com sessão segura. | Tela Login |
| RF04 | O sistema deve permitir sair da conta (logout), invalidando a sessão. | Menu |
| RF05 | O sistema deve permitir recuperar a senha mediante confirmação de e-mail e data de nascimento, gerando senha temporária. | Tela Recuperar |
| RF06 | O sistema deve permitir registrar denúncia com os campos: quem está denunciando, sobre o quê, categoria, cidade, bairro e descrição detalhada. | Tela Denúncias |
| RF07 | O sistema deve permitir anexar prova (imagem, PDF ou vídeo) com limite de 5 MB e validação de extensão. | Tela Denúncias |
| RF08 | O sistema deve listar de forma privativa e isolada as denúncias de cada usuário. | Tela Denúncias |
| RF09 | O sistema deve bloquear palavras ofensivas, termos de baixo calão e leet-speak (em nomes, cidades, assuntos e descrições). | Todas as telas |
| RF10 | O sistema deve exigir login ativo para permitir o envio de denúncia. | Tela Denúncias |
| RF11 | O sistema deve exibir os detalhes completos de uma denúncia (descrição, prova anexada e parecer de moderação) com controle de acesso. | Ver detalhes |
| RF12 | O sistema deve permitir excluir a conta definitivamente (cadastro, denúncias e provas físicas do disco), com confirmação obrigatória por senha (LGPD). | Menu |
| RF13 | O sistema deve dispor de painel do administrador para visualizar ocorrências e aprovar ou rejeitar cada uma. | Painel admin |
| RF14 | O sistema deve exibir publicamente no blog/feed apenas as denúncias aprovadas, com filtros por categoria e tags temáticas, sem exigir login. | Página pública / Home |
| RF15 | O sistema deve oferecer checagem de fatos em tempo real ("Fato ou Fake") com motor RAG nativo (SQLite FTS5) e transcrição de áudio. | Fato ou Fake (`/fato-ou-fake`) |
| RF16 | O sistema deve exigir a leitura e aceite do Termo de Declaração e Responsabilidade Legal com mecanismo *Scroll-to-Agree* antes de liberar o envio da denúncia. | Tela Denúncias |
| RF17 | O sistema deve fornecer API REST protegida por chave de autenticação (`X-API-Key`) para integração de robôs de triagem por IA com atribuição de score de confiança. | Endpoints `/api/v1/` |
| RF18 | O sistema deve disponibilizar barra fixa persistente de utilidade pública com discagem direta para telefones de emergência (190, 193, 192, 151, 199, 180, 181). | Rodapé Global |

---

## 3. Requisitos Não Funcionais

| Código | Requisito Não Funcional | Tipo |
|---|---|---|
| RNF01 | As páginas devem carregar com extrema rapidez (tempo de resposta do servidor < 50ms, Lighthouse Performance 98-100). | Desempenho |
| RNF02 | A senha deve ser armazenada utilizando hash criptográfico forte (`scrypt` com salt), nunca em texto puro. | Segurança |
| RNF03 | O sistema deve ser imune a SQL Injection mediante o uso estrito de consultas preparadas com parâmetros (`?`). | Segurança |
| RNF04 | Os anexos devem ter no máximo 5 MB, com whitelist de tipos MIME e rejeição estrita de executáveis (.exe, .sh, etc.). | Segurança |
| RNF05 | A interface deve adotar padrão Cyberpunk / Dark Neon (`#070a12`, texto em tons claros slate/white e realces neon `#ff007f`), alcançando conformidade WCAG AAA (100% no Lighthouse Acessibilidade). | Usabilidade / Design / Acessibilidade |
| RNF06 | O front-end deve utilizar CSS crítico minificado e inlined no `<head>` (`styles.min.css`) e scripts com atributo `defer`, eliminando bloqueios de renderização de rede e dependência de CDNs externas. | Compatibilidade & Desempenho |
| RNF07 | O sistema deve ser empacotado em contêiner Docker reproduzível via `docker compose`. | Portabilidade |
| RNF08 | Os dados (banco SQLite e arquivos físicos de upload) devem persistir em volumes mapeados após reinício do serviço. | Confiabilidade |
| RNF09 | O código deve ser organizado em arquitetura em camadas (Apresentação/Templates, Lógica de Negócio, Persistência, Filtro de Ofensas e Motor RAG). | Manutenibilidade |

---

## 4. Resumo

| Pergunta | Resposta |
|---|---|
| Funcional responde a qual pergunta? | O que o sistema faz |
| Não funcional responde a qual pergunta? | Como o sistema faz |
| Exemplo de funcional | RF06 — registrar denúncia; RF15 — checagem de fatos com RAG |
| Exemplo de não funcional | RNF02 — senha com hash scrypt; RNF05 — conformidade visual WCAG AAA |
