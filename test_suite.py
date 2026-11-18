"""
PROTEJAJÁ // SUÍTE DE TESTES E AUDITORIA COMPLETA
Validação automatizada de Requisitos Funcionais (RF01 - RF14),
Requisitos Não Funcionais (RNF01 - RNF10) e Casos de Uso.
"""

import io
import os
import sys
import time
import unittest
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

import database as db
import profanity
from app import create_app


class ProtejaJaTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["BOT_API_KEY"] = "teste-bot-key-123"
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    # ==========================================================
    # 1. SCHEMA E ESTRUTURA DO BANCO DE DADOS
    # ==========================================================

    def test_01_schema_e_migracao(self):
        """Valida se o schema do banco possui todas as colunas de IA, Termo Legal e Localização."""
        conn = db.get_connection()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(reports)").fetchall()}
        obrigatorias = {
            "score_confianca",
            "justificativa_ia",
            "data_analise_ia",
            "analisado_por_admin_id",
            "termo_aceito",
            "data_aceite_termo",
            "status",
            "cidade",
            "bairro",
        }
        for col in obrigatorias:
            self.assertIn(col, cols, f"Coluna '{col}' ausente no schema de reports!")

    # ==========================================================
    # 2. REQUISITOS FUNCIONAIS DE AUTENTICAÇÃO E CONTA (RF01 - RF05, RF12)
    # ==========================================================

    def test_02_RF01_cadastro_nome_sobrenome_obrigatorios(self):
        """RF01: Cadastro exige nome e sobrenome separados, e-mail, data_nasc, cidade, senha forte e confirmação."""
        res_sem_sobrenome = self.client.post(
            "/cadastro",
            data={
                "nome": "Carlos",
                "sobrenome": "",
                "email": "sem_sobrenome@teste.com",
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara - SP",
                "senha": "SenhaSegura123",
                "confirmar_senha": "SenhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Preencha todos os campos do cadastro", res_sem_sobrenome.data)

        # Senha fraca (sem maiúscula ou < 8 caracteres) deve ser rejeitada
        res_senha_fraca = self.client.post(
            "/cadastro",
            data={
                "nome": "Carlos",
                "sobrenome": "Oliveira",
                "email": "fraca@teste.com",
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara - SP",
                "senha": "senha123",
                "confirmar_senha": "senha123",
            },
            follow_redirects=True,
        )
        self.assertIn("mínimo 8 caracteres".encode("utf-8"), res_senha_fraca.data)

        # Senhas divergentes devem ser rejeitadas
        res_divergente = self.client.post(
            "/cadastro",
            data={
                "nome": "Carlos",
                "sobrenome": "Oliveira",
                "email": "divergente@teste.com",
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara - SP",
                "senha": "SenhaSegura123",
                "confirmar_senha": "OutraSenha123",
            },
            follow_redirects=True,
        )
        self.assertIn("As senhas não conferem".encode("utf-8"), res_divergente.data)

        # Cadastro válido SEM fornecer endereço (campo removido da tela de cadastro para proteção de dados)
        email_valido = f"user_rf01_{int(time.time() * 1000)}@teste.com"
        res_valido = self.client.post(
            "/cadastro",
            data={
                "nome": "Carlos",
                "sobrenome": "Oliveira",
                "email": email_valido,
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara - SP",
                "senha": "SenhaSegura123",
                "confirmar_senha": "SenhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Conta criada com sucesso", res_valido.data)
        user = db.usuario_por_email(email_valido)
        self.assertIsNotNone(user)
        self.assertEqual(user["nome"], "Carlos Oliveira")

    def test_03_RNF02_criptografia_senhas(self):
        """RNF02: Senha criptografada antes de gravar no banco, nunca em texto puro."""
        email = f"user_hash_{int(time.time() * 1000)}@teste.com"
        senha_pura = "MinhaSenhaSuperSecreta!123"
        self.client.post(
            "/cadastro",
            data={
                "nome": "Julia",
                "sobrenome": "Santos",
                "email": email,
                "data_nascimento": "1992-05-10",
                "cidade": "São Carlos - SP",
                "endereco": "Av Brasil, 500",
                "senha": senha_pura,
                "confirmar_senha": senha_pura,
            },
            follow_redirects=True,
        )
        user = db.usuario_por_email(email)
        self.assertIsNotNone(user)
        self.assertNotEqual(user["senha_hash"], senha_pura)
        self.assertTrue(user["senha_hash"].startswith("scrypt:"))
        self.assertTrue(check_password_hash(user["senha_hash"], senha_pura))

    def test_04_RF02_RF03_login_logout(self):
        """RF02 & RF03: Login com validação, ausência de recuperação de senha e logout seguro."""
        email = f"user_log_{int(time.time() * 1000)}@teste.com"
        senha = "SenhaCorreta123"
        self.client.post(
            "/cadastro",
            data={
                "nome": "Marcos",
                "sobrenome": "Silva",
                "email": email,
                "data_nascimento": "1988-10-20",
                "cidade": "Ribeirão Preto - SP",
                "endereco": "Rua 15, 200",
                "senha": senha,
                "confirmar_senha": senha,
            },
            follow_redirects=True,
        )
        res_login_get = self.client.get("/login")
        html_login = res_login_get.data.decode("utf-8")
        self.assertNotIn("/recuperar", html_login)
        self.assertNotIn("Esqueceu sua senha?", html_login)
        self.assertEqual(self.client.get("/recuperar").status_code, 404)

        res_erro = self.client.post("/login", data={"email": email, "senha": "senhaErrada"}, follow_redirects=True)
        self.assertIn(b"E-mail ou senha incorretos", res_erro.data)

        res_ok = self.client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)
        self.assertIn(b"Acesso liberado", res_ok.data)

        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"finalizada com seguran", res_logout.data)

    def test_06_RF12_exclusao_definitiva_conta_e_provas(self):
        """RF12: Excluir conta definitivamente (cadastro, denúncias e provas físicas) com senha."""
        email = f"user_del_{int(time.time() * 1000)}@teste.com"
        senha = "senhaDeletar123"
        uid = db.criar_usuario("Deletavel", "Silva", "1990-01-01", "Araraquara", "Rua X", generate_password_hash(senha))

        nome_anexo = f"anexo_teste_del_{int(time.time() * 1000)}.txt"
        caminho_anexo = os.path.join(db.UPLOAD_DIR, nome_anexo)
        with open(caminho_anexo, "w") as f:
            f.write("prova temporaria")
        self.assertTrue(os.path.exists(caminho_anexo))

        db.criar_denuncia(uid, "Loja Z", "Assunto Z", "Geral", "Desc Z", nome_anexo)

        with self.client.session_transaction() as sess:
            sess["user_id"] = uid

        res_erro = self.client.post("/excluir-conta", data={"senha": "senhaErrada"}, follow_redirects=True)
        self.assertIn(b"Senha incorreta", res_erro.data)
        self.assertIsNotNone(db.usuario_por_id(uid))

        res_ok = self.client.post("/excluir-conta", data={"senha": senha}, follow_redirects=True)
        self.assertIn(b"permanentemente expurgados", res_ok.data)
        self.assertIsNone(db.usuario_por_id(uid))
        self.assertEqual(len(db.denuncias_do_usuario(uid)), 0)
        self.assertFalse(os.path.exists(caminho_anexo))

    # ==========================================================
    # 3. REQUISITOS FUNCIONAIS DE DENÚNCIAS & MODERAÇÃO (RF06 - RF11, RF13, RF14)
    # ==========================================================

    def test_07_RF06_RF07_RF10_envio_denuncia_e_termo(self):
        """RF06, RF07 & RF10: Exigência de login, termo de responsabilidade e upload de prova."""
        with self.client.session_transaction() as sess:
            sess.clear()
        res_deslogado = self.client.get("/denuncias", follow_redirects=False)
        self.assertEqual(res_deslogado.status_code, 302)
        self.assertIn("/login", res_deslogado.headers["Location"])

        email = f"cidadao_{int(time.time() * 1000)}@teste.com"
        user_id = db.criar_usuario("Cidadão Teste", email, "15/05/1990", "São Paulo", "Av Paulista, 1000", generate_password_hash("123456"))

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id

        # Etapa 1 SEM termo: vai para a tela separada /denuncias/termo sem gravar ainda
        res_sem_termo = self.client.post(
            "/denuncias",
            data={
                "denunciado": "Supermercado X",
                "cidade": "Araraquara - SP",
                "bairro": "Centro",
                "assunto": "Produto com data vencida",
                "categoria": "Produto",
                "descricao": "Encontrei lote de laticínios fora do prazo de validade.",
            },
            follow_redirects=True,
        )
        self.assertIn("Termo de Declaração de Veracidade e Responsabilidade Legal".encode("utf-8"), res_sem_termo.data)
        self.assertEqual(len(db.denuncias_do_usuario(user_id)), 0)

        # Etapa 2: aceitar o termo em /denuncias/termo efetiva a denúncia
        res_etapa2 = self.client.post(
            "/denuncias/termo",
            data={"termo_responsabilidade": "1"},
            follow_redirects=True,
        )
        self.assertEqual(res_etapa2.status_code, 200)
        self.assertEqual(len(db.denuncias_do_usuario(user_id)), 1)

        # Envio COM termo e prova
        arquivo_prova = (io.BytesIO(b"conteudo-foto-prova-fake"), "foto_vencido.jpg")
        res_com_termo = self.client.post(
            "/denuncias",
            data={
                "denunciado": "Supermercado Savegnago",
                "cidade": "Araraquara - SP",
                "bairro": "Vila Xavier",
                "assunto": "Produto com data vencida",
                "categoria": "Produto",
                "descricao": "Encontrei lote de laticínios fora do prazo de validade nas gôndolas da filial.",
                "termo_responsabilidade": "1",
                "anexo": arquivo_prova,
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(res_com_termo.status_code, 200)

        denuncias = db.denuncias_do_usuario(user_id)
        self.assertGreater(len(denuncias), 0)
        ultima = denuncias[0]
        self.assertEqual(ultima["status"], db.STATUS_EM_ANALISE_IA)
        self.assertEqual(ultima["cidade"], "Araraquara - SP")
        self.assertEqual(ultima["bairro"], "Vila Xavier")
        self.assertIsNotNone(ultima["anexo"])

        ProtejaJaTestSuite.denuncia_teste_id = ultima["id"]

    def test_08_RF08_RF11_isolamento_e_detalhes(self):
        """RF08 & RF11: Listagem privativa e visualização de detalhes com barreira de acesso."""
        u1 = db.criar_usuario("User A", f"ua_{int(time.time()*1000)}@t.com", "1990-01-01", "Araraquara", "R1", generate_password_hash("123456"))
        u2 = db.criar_usuario("User B", f"ub_{int(time.time()*1000)}@t.com", "1990-01-01", "Araraquara", "R2", generate_password_hash("123456"))

        d1 = db.criar_denuncia(u1, "Empresa Alpha", "Assunto Alpha", "Geral", "Desc Alpha", None)
        d2 = db.criar_denuncia(u2, "Empresa Beta", "Assunto Beta", "Geral", "Desc Beta", None)

        with self.client.session_transaction() as sess:
            sess["user_id"] = u1

        res_lista = self.client.get("/denuncias")
        self.assertIn(b"Empresa Alpha", res_lista.data)
        self.assertNotIn(b"Empresa Beta", res_lista.data)

        res_alheio = self.client.get(f"/denuncias/{d2}", follow_redirects=True)
        self.assertIn(b"Den\xc3\xbancia n\xc3\xa3o encontrada ou n\xc3\xa3o pertence", res_alheio.data)

        res_proprio = self.client.get(f"/denuncias/{d1}")
        self.assertIn(b"Empresa Alpha", res_proprio.data)
        self.assertIn(b"Desc Alpha", res_proprio.data)

    def test_09_RF09_filtro_antiofensa(self):
        """RF09: Bloqueio de ofensas, termos de baixo calão e leet-speak."""
        self.assertTrue(profanity.contem_ofensa("Voce e um fdp"))
        self.assertTrue(profanity.contem_ofensa("vai tomar no cu"))
        self.assertTrue(profanity.contem_ofensa("que p0rra e essa"))
        self.assertTrue(profanity.contem_ofensa("atendimento f0dido"))
        self.assertFalse(profanity.contem_ofensa("Supermercado Savegnago vendeu carne fora da validade"))

        res = self.client.post(
            "/cadastro",
            data={
                "nome": "Otario",
                "sobrenome": "Silva",
                "email": f"bad_{int(time.time()*1000)}@t.com",
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara - SP",
                "endereco": "Rua 1",
                "senha": "SenhaSegura123",
                "confirmar_senha": "SenhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"palavras ofensivas", res.data)

    def test_10_RF13_RF14_moderacao_admin_e_publicacao(self):
        """RF13 & RF14: Moderação pelo admin e publicação pública no feed com tags."""
        nome_empresa = f"Mercado Inedito {int(time.time() * 1000)}"
        admin = db.usuario_por_email(db.ADMIN_EMAIL)
        u = db.criar_usuario("Cidadao Y", f"cid_{int(time.time()*1000)}@t.com", "1990-01-01", "Araraquara", "Rua 1", generate_password_hash("123456"))
        d_id = db.criar_denuncia(u, nome_empresa, "Cobrança indevida", "Serviço", "Cobraram taxa abusiva sem aviso prévio.", None)

        # Não logado não enxerga ainda
        res_pub_antes = self.client.get("/denuncias-publicas")
        self.assertNotIn(nome_empresa.encode("utf-8"), res_pub_antes.data)

        # Admin loga e aprova
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin["id"]

        res_moderar = self.client.post(f"/admin/moderar/{d_id}", data={"status": "APROVADO"}, follow_redirects=True)
        self.assertEqual(res_moderar.status_code, 200)

        # Visitante enxerga agora
        with self.client.session_transaction() as sess:
            sess.clear()
        res_pub_depois = self.client.get("/denuncias-publicas")
        self.assertIn(nome_empresa.encode("utf-8"), res_pub_depois.data)

    # ==========================================================
    # 4. API REST DE TRIAGEM COM IA & BOT
    # ==========================================================

    def test_11_api_bot_triagem_e_patch(self):
        """Valida autenticação via token e atualização de triagem com score e justificativa."""
        denuncia_id = getattr(self, "denuncia_teste_id", None)
        self.assertIsNotNone(denuncia_id, "ID da denúncia de teste ausente!")

        res_sem_auth = self.client.get("/api/v1/denuncias/pendentes")
        self.assertEqual(res_sem_auth.status_code, 401)

        headers = {"X-API-Key": "teste-bot-key-123"}
        res_auth = self.client.get("/api/v1/denuncias/pendentes", headers=headers)
        self.assertEqual(res_auth.status_code, 200)

        payload = {
            "status": "ALERTA_REVISAO_MANUAL",
            "score_confianca": 0.75,
            "justificativa_ia": "Análise documental pendente de conferência manual.",
        }
        res_patch = self.client.patch(
            f"/api/v1/denuncias/{denuncia_id}/triagem",
            json=payload,
            headers=headers,
        )
        self.assertEqual(res_patch.status_code, 200)
        dados = res_patch.get_json()
        self.assertTrue(dados["sucesso"])
        self.assertEqual(dados["status_atual"], "ALERTA_REVISAO_MANUAL")
        self.assertEqual(dados["score_confianca"], 0.75)

    # ==========================================================
    # 5. PORTAL DE NOTÍCIAS E REMOÇÃO DE FATO OU FAKE / RAG
    # ==========================================================

    def test_12_portal_noticias_e_remocao_fato_ou_fake(self):
        """Valida página /noticias (Portal de Notícias e Alertas) e remoção de /fato-ou-fake e /api/v1/checar-fato."""
        res_pagina = self.client.get("/noticias")
        self.assertEqual(res_pagina.status_code, 200)
        self.assertIn(b"Portal de Not\xc3\xadcias e Alertas", res_pagina.data)
        self.assertIn(b"Not\xc3\xadcias e Alertas Recentes", res_pagina.data)

        self.assertEqual(self.client.get("/fato-ou-fake").status_code, 404)
        self.assertEqual(
            self.client.post("/api/v1/checar-fato", json={"texto": "teste"}).status_code,
            404,
        )

    # ==========================================================
    # 6. REQUISITOS NÃO FUNCIONAIS (RNF01 - RNF10) & SEO
    # ==========================================================

    def test_13_RNF01_desempenho_rotas_principais(self):
        """RNF01: Resposta em poucos segundos (localmente < 500ms)."""
        rotas = ["/home", "/denuncias-publicas", "/noticias", "/login", "/cadastro"]
        for r in rotas:
            t0 = time.time()
            res = self.client.get(r)
            duracao_ms = (time.time() - t0) * 1000
            self.assertEqual(res.status_code, 200)
            self.assertLess(duracao_ms, 500, f"Rota {r} lenta: {duracao_ms:.1f}ms")

    def test_14_RNF03_resistencia_sql_injection(self):
        """RNF03: Consultas com parâmetros protegidas contra SQL Injection."""
        payload_sqli = "' OR '1'='1"
        res_login = self.client.post("/login", data={"email": payload_sqli, "senha": payload_sqli})
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"E-mail ou senha incorretos", res_login.data)

        res_busca = self.client.get(f"/denuncias-publicas?q={payload_sqli}")
        self.assertEqual(res_busca.status_code, 200)

    def test_15_RNF04_limite_tamanho_e_tipo_anexo(self):
        """RNF04: Limite de 5 MB e bloqueio de tipos não permitidos (.exe, .sh)."""
        uid = db.criar_usuario("User Anexo", f"anx_{int(time.time()*1000)}@t.com", "1990-01-01", "Araraquara", "R1", generate_password_hash("123456"))
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid

        arquivo_executavel = (io.BytesIO(b"MALICIOUS_BYTES"), "malware.exe")
        res = self.client.post(
            "/denuncias",
            data={
                "denunciado": "Loja A",
                "cidade": "Araraquara - SP",
                "bairro": "Centro",
                "assunto": "Teste anexo proibido",
                "categoria": "Geral",
                "descricao": "Tentativa de envio de executavel.",
                "termo_responsabilidade": "1",
                "anexo": arquivo_executavel,
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertIn(b"Foto ou anexo n\xc3\xa3o recomendado", res.data)

    def test_16_seo_seguranca_http_e_telefones_uteis(self):
        """RNF05, RNF06 & SEO: Headers nosniff, mascaramento Server, robots.txt, sitemap e emergências."""
        res_home = self.client.get("/home")
        self.assertEqual(res_home.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res_home.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(res_home.headers.get("Server"), "ProtejaJa-Edge")

        html = res_home.data.decode("utf-8")
        self.assertIn("190", html)
        self.assertIn("Polícia Militar", html)
        self.assertIn("193", html)
        self.assertIn("Bombeiros", html)
        self.assertIn("192", html)
        self.assertIn("SAMU", html)
        self.assertIn("151", html)
        self.assertIn("Procon", html)

        res_robots = self.client.get("/robots.txt")
        self.assertEqual(res_robots.status_code, 200)
        self.assertIn(b"User-agent", res_robots.data)

        res_sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(res_sitemap.status_code, 200)
        self.assertIn(b"<urlset", res_sitemap.data)

    def test_17_melhorias_ui_ux_a11y(self):
        """Valida as 3 melhorias de UI/UX: Navbar A11y, Grade Nativa de Recursos e Badge Fato/Fake."""
        res_home = self.client.get("/home")
        self.assertEqual(res_home.status_code, 200)
        html_home = res_home.data.decode("utf-8")

        # 1. Navbar semântica com foco em acessibilidade e visibilidade do MENU
        self.assertIn('<button id="btnMenuToggle" type="button"', html_home)
        self.assertIn('aria-label="Abrir menu de navegação"', html_home)
        self.assertIn('aria-expanded="false"', html_home)
        self.assertIn('menu-icon-svg', html_home)
        self.assertIn('MENU', html_home)

        # 2. Agrupamento da seção de recursos em /diferencial com tag section, aria-labelledby e grid nativo
        res_dif = self.client.get("/diferencial")
        self.assertEqual(res_dif.status_code, 200)
        html_dif = res_dif.data.decode("utf-8")
        self.assertIn('aria-labelledby="titulo-recursos-principais"', html_dif)
        self.assertIn('id="titulo-recursos-principais" class="sr-only"', html_dif)
        self.assertIn("card-recurso-destaque", html_dif)
        self.assertIn("grid-recursos-nativa", html_dif)
        self.assertIn("Novo Recurso", html_dif)
        self.assertIn("Prazo Oficial", html_dif)
        self.assertIn("Indexação Pública", html_dif)
        self.assertIn("Comprovação", html_dif)

        # 3. Portal de Notícias e Alertas acessível e sem verificador quebrado
        res_not = self.client.get("/noticias")
        self.assertEqual(res_not.status_code, 200)
        html_not = res_not.data.decode("utf-8")
        self.assertIn("Portal de Notícias e Alertas", html_not)
        self.assertNotIn("resultadoBadgeAlert", html_not)

        # 4. Validação das classes CSS de alto contraste e foco visível no CSS inlined
        self.assertIn(".menu-toggle-btn:focus-visible", html_home)
        self.assertIn("status-fato", html_home)
        self.assertIn("status-fake", html_home)
        self.assertIn("status-alerta", html_home)
        self.assertIn("grid-template-columns:repeat(auto-fit,minmax(280px,1fr))", html_home.replace(" ", ""))

    def test_20_autocomplete_municipios_ibge_e_validacao(self):
        """Valida endpoint /api/municipios (<100ms, 5.570 municípios IBGE) e cadastro/denúncia nacional."""
        for prefixo, esperado in [
            ("arara", "Araraquara - SP"),
            ("matao", "Matão - SP"),
            ("curit", "Curitiba - PR"),
        ]:
            t0 = time.perf_counter()
            res = self.client.get(f"/api/municipios?q={prefixo}")
            dt_ms = (time.perf_counter() - t0) * 1000
            self.assertEqual(res.status_code, 200)
            self.assertLess(dt_ms, 100.0)
            lista = res.get_json().get("municipios", [])
            self.assertLessEqual(len(lista), 10)
            self.assertIn(esperado, lista)

        # Município inválido deve ser rejeitado no cadastro
        res_inv = self.client.post(
            "/cadastro",
            data={
                "nome": "Teste",
                "sobrenome": "Nacional",
                "email": f"inv_mun_{int(time.time()*1000)}@t.com",
                "data_nascimento": "1995-03-10",
                "cidade": "Cidade Inventada - XX",
                "senha": "SenhaSegura123",
                "confirmar_senha": "SenhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn("Selecione um município brasileiro válido".encode("utf-8"), res_inv.data)

        # Cadastro em outro estado (Curitiba - PR) deve funcionar
        email_pr = f"pr_{int(time.time()*1000)}@t.com"
        res_pr = self.client.post(
            "/cadastro",
            data={
                "nome": "Ana",
                "sobrenome": "Paraná",
                "email": email_pr,
                "data_nascimento": "1995-03-10",
                "cidade": "Curitiba - PR",
                "senha": "SenhaSegura123",
                "confirmar_senha": "SenhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Conta criada com sucesso", res_pr.data)

        user_pr = db.usuario_por_email(email_pr)
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_pr["id"]

        res_den_ba = self.client.post(
            "/denuncias",
            data={
                "denunciado": "Loja Nacional",
                "cidade": "Salvador - BA",
                "bairro": "Pituba",
                "assunto": "Cobrança indevida",
                "categoria": "Serviço",
                "descricao": "Cobraram taxa adicional sem aviso prévio no caixa.",
                "termo_responsabilidade": "1",
            },
            follow_redirects=True,
        )
        self.assertEqual(res_den_ba.status_code, 200)
        self.assertEqual(db.denuncias_do_usuario(user_pr["id"])[0]["cidade"], "Salvador - BA")

    def test_21_validacao_maioridade_18_anos(self):
        """Valida bloqueio de cadastro para menores de 18 anos."""
        import datetime
        menor_data = (datetime.date.today().replace(year=datetime.date.today().year - 15)).isoformat()
        email_menor = f"menor_{int(time.time()*1000)}@t.com"
        res = self.client.post(
            "/cadastro",
            data={
                "nome": "João",
                "sobrenome": "Menor",
                "email": email_menor,
                "data_nascimento": menor_data,
                "cidade": "São Paulo - SP",
                "senha": "SenhaSegura123",
                "confirmar_senha": "SenhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"maiores de 18 anos", res.data)
        self.assertIsNone(db.usuario_por_email(email_menor))

    def test_22_campos_obrigatorios_asterisco_vermelho_e_portal_noticias(self):
        """Valida Portal de Notícias ativo e asterisco vermelho (*) nos campos obrigatórios dos formulários."""
        res_not = self.client.get("/noticias")
        html_not = res_not.data.decode("utf-8")
        self.assertIn("Portal de Notícias e Alertas", html_not)
        self.assertIn("Golpes e Fraudes", html_not)
        self.assertIn("Impostos e Dinheiro Público", html_not)
        self.assertNotIn("Verificar Fatos Agora", html_not)

        asterisco = '<span style="color:#ef4444" aria-hidden="true">*</span>'
        for rota in ["/cadastro", "/login"]:
            html = self.client.get(rota).data.decode("utf-8")
            self.assertIn(asterisco, html)

        html_cad = self.client.get("/cadastro").data.decode("utf-8")
        self.assertIn('name="confirmar_senha"', html_cad)
        self.assertIn('minlength="8"', html_cad)

        # Rotas autenticadas (/denuncias e /excluir-conta) também exibem asterisco vermelho
        admin = db.usuario_por_email(db.ADMIN_EMAIL)
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin["id"]
        for rota_auth in ["/denuncias", "/excluir-conta"]:
            html_auth = self.client.get(rota_auth).data.decode("utf-8")
            self.assertIn(asterisco, html_auth)

    def test_23_curtidas_ranking_e_comentarios_publicos(self):
        """Valida curtida ('Também fui afetado'), ranking e comentários com login obrigatório e filtro antiofensa."""
        u = db.criar_usuario("Cidadao Social", f"soc_{int(time.time()*1000)}@t.com", "1990-01-01", "São Paulo - SP", "", generate_password_hash("123456"))
        d_id = db.criar_denuncia(u, "Empresa Teste Ranking", "Cobrança abusiva", "Serviço", "Relato para teste de ranking e comentários.", None, cidade="São Paulo - SP", bairro="Centro")
        db.atualizar_status_denuncia(d_id, db.STATUS_APROVADO)

        # Garante sessão deslogada antes de testar comportamento de visitante
        with self.client.session_transaction() as sess:
            sess.clear()

        # Deslogado vê o botão de curtir apontando para /cadastro e não pode curtir/comentar via POST
        res_anon = self.client.get("/denuncias-publicas")
        self.assertIn('href="/cadastro"', res_anon.data.decode("utf-8"))
        self.assertEqual(self.client.post(f"/denuncias-publicas/{d_id}/curtir").status_code, 302)
        self.assertEqual(self.client.post(f"/denuncias-publicas/{d_id}/comentar", data={"comentario": "Oi"}).status_code, 302)

        with self.client.session_transaction() as sess:
            sess["user_id"] = u

        # Curtir incrementa e aparece no ranking
        res_curtir = self.client.post(f"/denuncias-publicas/{d_id}/curtir", follow_redirects=True)
        self.assertEqual(res_curtir.status_code, 200)
        html_pub = res_curtir.data.decode("utf-8")
        self.assertIn("Também fui afetado (1)", html_pub)
        self.assertIn("Ranking — Casos com Mais Pessoas Afetadas", html_pub)

        # Comentário válido aparece; ofensivo é bloqueado
        res_com_ok = self.client.post(
            f"/denuncias-publicas/{d_id}/comentar",
            data={"comentario": "Passei pelo mesmo problema nessa unidade."},
            follow_redirects=True,
        )
        self.assertIn("Passei pelo mesmo problema nessa unidade.", res_com_ok.data.decode("utf-8"))

        res_com_bad = self.client.post(
            f"/denuncias-publicas/{d_id}/comentar",
            data={"comentario": "bando de fdp"},
            follow_redirects=True,
        )
        self.assertIn("termos ofensivos", res_com_bad.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()

