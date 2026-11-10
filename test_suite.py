"""
PROTEJAJÁ // SUÍTE DE TESTES E AUDITORIA COMPLETA
Validação automatizada de Requisitos Funcionais (RF01 - RF14),
Requisitos Não Funcionais (RNF01 - RNF09), Casos de Uso e Motor RAG.
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
import fact_checker
import profanity
import rag_engine
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
        """RF01: Cadastro exige nome e sobrenome separados, e-mail, data_nasc, cidade e senha (sem exigência de endereço)."""
        res_sem_sobrenome = self.client.post(
            "/cadastro",
            data={
                "nome": "Carlos",
                "sobrenome": "",
                "email": "sem_sobrenome@teste.com",
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara",
                "senha": "senhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Preencha todos os campos do cadastro", res_sem_sobrenome.data)

        # Cadastro válido SEM fornecer endereço (campo removido da tela de cadastro para proteção de dados)
        email_valido = f"user_rf01_{int(time.time() * 1000)}@teste.com"
        res_valido = self.client.post(
            "/cadastro",
            data={
                "nome": "Carlos",
                "sobrenome": "Oliveira",
                "email": email_valido,
                "data_nascimento": "1990-01-01",
                "cidade": "Araraquara",
                "senha": "senhaSegura123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Conta criada com sucesso", res_valido.data)
        user = db.usuario_por_email(email_valido)
        self.assertIsNotNone(user)
        self.assertEqual(user["nome"], "Carlos Oliveira")

    def test_03_RF02_RNF02_criptografia_senhas(self):
        """RF02 & RNF02: Senha criptografada antes de gravar no banco, nunca em texto puro."""
        email = f"user_hash_{int(time.time() * 1000)}@teste.com"
        senha_pura = "MinhaSenhaSuperSecreta!123"
        self.client.post(
            "/cadastro",
            data={
                "nome": "Julia",
                "sobrenome": "Santos",
                "email": email,
                "data_nascimento": "1992-05-10",
                "cidade": "São Carlos",
                "endereco": "Av Brasil, 500",
                "senha": senha_pura,
            },
            follow_redirects=True,
        )
        user = db.usuario_por_email(email)
        self.assertIsNotNone(user)
        self.assertNotEqual(user["senha_hash"], senha_pura)
        self.assertTrue(user["senha_hash"].startswith("scrypt:"))
        self.assertTrue(check_password_hash(user["senha_hash"], senha_pura))

    def test_04_RF03_RF04_login_logout(self):
        """RF03 & RF04: Login com validação e encerramento de sessão com segurança."""
        email = f"user_log_{int(time.time() * 1000)}@teste.com"
        senha = "senhaCorreta123"
        self.client.post(
            "/cadastro",
            data={
                "nome": "Marcos",
                "sobrenome": "Silva",
                "email": email,
                "data_nascimento": "1988-10-20",
                "cidade": "Ribeirão Preto",
                "endereco": "Rua 15, 200",
                "senha": senha,
            },
            follow_redirects=True,
        )
        res_erro = self.client.post("/login", data={"email": email, "senha": "senhaErrada"}, follow_redirects=True)
        self.assertIn(b"E-mail ou senha incorretos", res_erro.data)

        res_ok = self.client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)
        self.assertIn(b"Acesso liberado", res_ok.data)

        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"finalizada com seguran", res_logout.data)

    def test_05_RF05_recuperacao_senha(self):
        """RF05: Recuperar senha mediante e-mail e data de nascimento gerando senha temporária."""
        email = f"user_recup_{int(time.time() * 1000)}@teste.com"
        nasc = "1995-12-05"
        self.client.post(
            "/cadastro",
            data={
                "nome": "Paula",
                "sobrenome": "Teixeira",
                "email": email,
                "data_nascimento": nasc,
                "cidade": "Araraquara",
                "endereco": "Rua 9 de Julho, 1200",
                "senha": "senhaOriginal123",
            },
            follow_redirects=True,
        )
        res_falha = self.client.post("/recuperar", data={"email": email, "data_nascimento": "1990-01-01"}, follow_redirects=True)
        self.assertIn(b"Dados n\xc3\xa3o conferem", res_falha.data)

        res_sucesso = self.client.post("/recuperar", data={"email": email, "data_nascimento": nasc}, follow_redirects=True)
        self.assertIn(b"NOVA SENHA GERADA PARA:", res_sucesso.data)

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

        # Envio SEM aceitar o termo
        res_sem_termo = self.client.post(
            "/denuncias",
            data={
                "denunciado": "Supermercado X",
                "cidade": "Araraquara",
                "bairro": "Centro",
                "assunto": "Produto com data vencida",
                "categoria": "Produto",
                "descricao": "Encontrei lote de laticínios fora do prazo de validade.",
            },
            follow_redirects=True,
        )
        self.assertIn("Termo de Declaração e Responsabilidade Legal".encode("utf-8"), res_sem_termo.data)

        # Envio COM termo e prova
        arquivo_prova = (io.BytesIO(b"conteudo-foto-prova-fake"), "foto_vencido.jpg")
        res_com_termo = self.client.post(
            "/denuncias",
            data={
                "denunciado": "Supermercado Savegnago",
                "cidade": "Araraquara",
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
        self.assertEqual(ultima["cidade"], "Araraquara")
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
                "cidade": "Araraquara",
                "endereco": "Rua 1",
                "senha": "senha123",
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
    # 5. NOVO RECURSO: CHECAGEM DE FATOS & MOTOR RAG NATIVO
    # ==========================================================

    def test_12_fato_ou_fake_com_auditoria_automatizada(self):
        """Valida página /fato-ou-fake e API /api/v1/checar-fato com auditoria automatizada e fontes oficiais."""
        res_pagina = self.client.get("/fato-ou-fake")
        self.assertEqual(res_pagina.status_code, 200)
        self.assertIn(b"Checagem de Fatos em Tempo Real", res_pagina.data)
        self.assertIn("Auditoria Automatizada".encode("utf-8"), res_pagina.data)

        # Teste de checagem com recuperação e fundamentação oficial
        res_api = self.client.post("/api/v1/checar-fato", json={
            "texto": "Receita Federal vai começar a cobrar imposto no Pix"
        })
        self.assertEqual(res_api.status_code, 200)
        dados = res_api.get_json()
        self.assertTrue(dados.get("sucesso"))
        self.assertIn("status", dados)
        self.assertIn("parecer", dados)

    # ==========================================================
    # 6. REQUISITOS NÃO FUNCIONAIS (RNF01 - RNF09) & SEO
    # ==========================================================

    def test_13_RNF01_desempenho_rotas_principais(self):
        """RNF01: Resposta em poucos segundos (localmente < 500ms)."""
        rotas = ["/home", "/denuncias-publicas", "/fato-ou-fake", "/login", "/cadastro"]
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
                "cidade": "Araraquara",
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

        # 2. Agrupamento da seção de recursos com tag section, aria-labelledby e grid nativo
        self.assertIn('aria-labelledby="titulo-recursos-principais"', html_home)
        self.assertIn('id="titulo-recursos-principais" class="sr-only"', html_home)
        self.assertIn("card-recurso-destaque", html_home)
        self.assertIn("grid-recursos-nativa", html_home)
        self.assertIn("Novo Recurso", html_home)
        self.assertIn("Prazo Oficial", html_home)
        self.assertIn("Indexação Pública", html_home)
        self.assertIn("Comprovação", html_home)

        # 3. Interface de Resultado Fato ou Fake com role status e aria-live polite
        res_fake = self.client.get("/fato-ou-fake")
        self.assertEqual(res_fake.status_code, 200)
        html_fake = res_fake.data.decode("utf-8")

        self.assertIn('id="resultadoBadgeAlert"', html_fake)
        self.assertIn('role="status"', html_fake)
        self.assertIn('aria-live="polite"', html_fake)

        # 4. Validação das classes CSS de alto contraste e foco visível no CSS inlined
        self.assertIn(".menu-toggle-btn:focus-visible", html_home)
        self.assertIn("status-fato", html_home)
        self.assertIn("status-fake", html_home)
        self.assertIn("status-alerta", html_home)
        self.assertIn("grid-template-columns:repeat(auto-fit,minmax(280px,1fr))", html_home.replace(" ", ""))

    def test_18_agentic_web_search_pipeline(self):
        """Valida o pipeline de Agentic Web Search em tempo real com Filtro de Autoridade e schema JSON."""
        from agentic_checker import processar_entrada_usuario, RESULTADO_INCONCLUSIVO_PADRAO

        # 1. Validação de contrato estruturado
        resultado = processar_entrada_usuario("Boato sobre confisco da poupança")
        self.assertIn("status", resultado)
        self.assertIn(resultado["status"], ("fato", "fake", "alerta", "inconclusivo"))
        self.assertIsInstance(resultado["confianca"], int)
        self.assertIsInstance(resultado["parecer"], str)
        self.assertIn("fonte_recomendada", resultado)
        self.assertIn("nome", resultado["fonte_recomendada"])
        self.assertIn("url", resultado["fonte_recomendada"])

        # 2. Validação da Regra de Ouro: boato local sem cobertura vira INCONCLUSIVO
        res_local = processar_entrada_usuario("O cachorro do Zé da esquina voou em Piracicaba às 3h")
        self.assertEqual(res_local["status"], "inconclusivo")
        self.assertEqual(res_local["fonte_recomendada"]["nome"], "Inexistente")
        self.assertIsNone(res_local["fonte_recomendada"]["url"])

        # 3. Validação de robustez contra exceções / entrada vazia
        res_vazia = processar_entrada_usuario("")
        self.assertEqual(res_vazia["status"], "inconclusivo")

        # 4. Validação da API REST /api/v1/checar-fato
        res_api = self.client.post("/api/v1/checar-fato", json={"texto": "Confisco da poupança"})
        self.assertEqual(res_api.status_code, 200)
        dados = res_api.get_json()
        self.assertTrue(dados.get("sucesso"))
        self.assertIn("status", dados)
        self.assertIn("confianca", dados)
        self.assertIn("fonte_recomendada", dados)

    def test_19_protecao_propriedade_intelectual_e_blackbox_copywriting(self):
        """Valida que todos os jargões técnicos de IA/RAG foram expurgados do Backend e Frontend."""
        import json
        import fact_checker

        # 1. Validação de caixa-preta no Backend (analisar_fato)
        resultado = fact_checker.analisar_fato("O governo vai confiscar a poupança nesta semana")
        self.assertTrue(resultado.get("sucesso"))
        self.assertEqual(resultado.get("origem"), "Motor de Verificação Proteja-Já")

        resultado_json = json.dumps(resultado, ensure_ascii=False).lower()
        self.assertNotIn("rag", resultado_json)
        self.assertNotIn("agentic", resultado_json)
        self.assertNotIn("filtro de autoridade", resultado_json)
        self.assertNotIn("algoritmo", resultado_json)
        self.assertNotIn("heurística", resultado_json)
        self.assertNotIn("pesquisa web em tempo real", resultado_json)

        # 2. Validação de copywriting institucional no Frontend (/fato-ou-fake)
        res_fake = self.client.get("/fato-ou-fake")
        self.assertEqual(res_fake.status_code, 200)
        html_fake = res_fake.data.decode("utf-8")

        self.assertNotIn("Validar Notícia Agora com RAG", html_fake)
        self.assertNotIn("Inteligência RAG", html_fake)
        self.assertNotIn("Inteligência Factual", html_fake)
        self.assertNotIn("Validação RAG", html_fake)
        self.assertNotIn("Evidência RAG recuperada", html_fake)

        self.assertIn("Verificar Fatos Agora", html_fake)
        self.assertIn("Auditoria Automatizada Proteja-Já", html_fake)
        self.assertIn("Fundamentação Oficial e Registros Institucionais", html_fake)


if __name__ == "__main__":
    unittest.main()

