# ProtejaJA — Wireframe das Telas e Manipulação de Imagem

---

## PARTE 1 — WIREFRAME (o esboço das telas)

**O que é um wireframe?**
É o **rascunho** da tela: mostra onde ficam os botões, campos e textos, antes
de "colorir". É a planta baixa do site.

---

### 1.1 Wireframe — Tela Home

```
+----------------------------------------------------------+
| Logo ProtejaJA      Home   Entrar   [Cadastrar]   (menu) |
+----------------------------------------------------------+
|                                                          |
|                 (etiqueta) Projeto Integrador            |
|                                                          |
|                ## ProtejaJA  ##                          |
|                                                          |
|          "Plataforma para registrar denúncias            |
|           com segurança..."                              |
|                                                          |
|   [ SENHAS ]      [ FILTRO ]       [ ANEXO ]             |
|   criptografadas  antiofensa        de prova             |
|      (card)          (card)           (card)             |
|                                                          |
|        [ Criar conta ]        [ Entrar ]                 |
|                                                          |
+----------------------------------------------------------+
```

**Características:** título centralizado, 3 cards explicativos, botão rosa.

---

### 1.2 Wireframe — Tela Cadastro (card central)

```
+----------------------------------------------------------+
| Logo ProtejaJA      Home   Entrar   [Cadastrar]   (menu) |
+----------------------------------------------------------+
|              +-----------------------------+              |
|              |     Criar conta             |              |
|              |  Preencha seus dados...     |              |
|              |-----------------------------|              |
|              | Primeiro Nome * | Sobrenome * |              |
|              | E-mail *        | Nasc. (18+) * |            |
|              | Município (IBGE) * [________] |              |
|              | Senha *           [________] |              |
|              | [    CADASTRAR    ] (rosa)  |              |
|              | Já tem conta? Entrar        |              |
|              +-----------------------------+              |
+----------------------------------------------------------+
```

**Campos obrigatórios (`* (obrigatório)`):** primeiro nome, sobrenome, e-mail, data de nascimento (mínimo 18 anos), município (`Cidade - UF` via autocomplete IBGE) e senha.

---

### 1.3 Wireframe — Tela Login (card central)

```
+----------------------------------------------------------+
| Logo ProtejaJA      Home   Entrar   [Cadastrar]   (menu) |
+----------------------------------------------------------+
|              +-----------------------------+              |
|              |        Entrar               |              |
|              |  Acesse sua conta...        |              |
|              |-----------------------------|              |
|              | E-mail  [________]          |              |
|              | Senha   [________]          |              |
|              | [    ENTRAR    ] (neon)     |              |
|              |                             |              |
|              | Não tem conta? Cadastrar    |              |
|              +-----------------------------+              |
+----------------------------------------------------------+
```

---

### 1.4 Wireframe — Tela Denúncias (a principal)

```
+----------------------------------------------------------+
| Logo ProtejaJA   Home  Denúncias  Olá, X    [Sair] (menu)|
+----------------------------------------------------------+
|  Enviar denúncia                                          |
| --------------------------------------------------------- |
| | Quem você está denunciando? *  [ Hipermercado    ]   |   |
| | Sobre o que? *                [ Produto vencido ]   |   |
| | Categoria [ Produto  v ]                             |  |
| | Município (IBGE) * [______]  Bairro * [______]       |  |
| | Descrição * [______________________]                 |  |
| | Prova (anexo) [ Escolher arquivo ] até 5 MB          |  |
| | [x] Li e aceito o Termo de Responsabilidade Legal    |  |
| | [     ENVIAR DENÚNCIA    ] (neon)                    |  |
| --------------------------------------------------------- |
|                                                          |
|  Minhas denúncias                                        |
| --------------------------------------------------------- |
| | (Produto) 12/09/2026                                  |  |
| | **Hipermercado**  Produto vencido                    |  |
| | Comprei e não quiseram trocar...  📎 Ver anexo        |  |
| --------------------------------------------------------- |
+----------------------------------------------------------+
```

**Esta tela contém os campos do formulário de denúncia:**
1. Quem você está denunciando? (ex.: **Hipermercado**)
2. Sobre o que? (ex.: produto vencido)
3. Categoria
4. Município (`Cidade - UF` via autocomplete IBGE) e Bairro
5. Descrição
6. Anexo de prova (imagem/PDF/vídeo até 5 MB)
7. Aceite do Termo de Responsabilidade Legal

---

## PARTE 2 — MANIPULAÇÃO DE IMAGEM

### 2.1 A identidade visual (cores do projeto)

O tema atual adota o padrão **Dark Neon / Cyberpunk** com alto contraste (conformidade WCAG AAA):

| Elemento | Cor | Código (hex) |
|---|---|---|
| Fundo da página | Azul-escuro / Preto profundo | `#070a12` |
| Destaque / Botão principal | **Rosa Neon** | `#ff007f` |
| Texto principal | Branco / Slate claro | `#f8fafc` / `#cbd5e1` |
| Fundo dos cards | Slate escuro translúcido | `#0f172a` |

### 2.2 Como o site "manipula" as imagens (provas de denúncia)

O site recebe o arquivo e faz um tratamento antes de guardar:

1. **Verifica o tipo** — aceita apenas extensões permitidas (imagens, PDF e vídeos configurados em `ALLOWED_EXTENSIONS`).
2. **Limita o tamanho** — máximo de **5 MB** (`MAX_CONTENT_LENGTH`).
3. **Renomeia com nome seguro** — usa `secure_filename` + prefixo UUID para evitar sobrescrita e caracteres perigosos.
4. **Salva em pasta separada** — `backend/uploads/`, fora do banco de dados.
5. **Gera pré-visualização** — o JavaScript lê o arquivo e mostra uma **miniatura** antes de enviar.

Fluxo do anexo:

```
Usuário escolhe o arquivo
      |
      v
Navegador mostra miniatura (pré-visualização)
      |
      v
Servidor verifica tipo + tamanho (máx 5 MB)
      |
      v
Salva com nome seguro em backend/uploads/
      |
      v
Denúncia lista o anexo com link "Ver anexo"
```

### 2.3 Manipulação visual no front-end (CSS)

O estilo é carregado via `home/css/styles.min.css` (inlined no `<head>` para carregamento rápido) e `home/css/styles.css`, aplicando:
- Cards com `border-radius` e bordas sutis sobre o fundo escuro `#070a12`;
- Botões com realce neon `#ff007f` e feedback visual no `:hover`;
- Miniaturas com `object-cover` e bordas arredondadas na pré-visualização.