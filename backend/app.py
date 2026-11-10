import gzip
import os
import re
import secrets
import uuid
from functools import wraps

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import database as db
import fact_checker
from profanity import contem_ofensa, sanitizar

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOME_DIR = os.path.join(BASE_DIR, "home")
TEMPLATE_DIR = os.path.join(BASE_DIR, "backend", "templates")
UPLOAD_DIR = db.UPLOAD_DIR

BOT_API_KEY = os.environ.get("BOT_API_KEY", "protejaja-bot-secret-key-2026")
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "webp", "heic", "heif", "pdf", "mp4", "mov"}
MAX_ANEXO = 5 * 1024 * 1024

CSS_FILE_PATH = os.path.join(HOME_DIR, "css", "styles.min.css")
CRITICAL_CSS = ""
if os.path.exists(CSS_FILE_PATH):
    try:
        with open(CSS_FILE_PATH, "r", encoding="utf-8") as _f:
            CRITICAL_CSS = _f.read()
    except Exception:
        CRITICAL_CSS = ""


def arquivo_permitido(nome):
    return "." in nome and nome.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


def login_obrigatorio(visao):
    @wraps(visao)
    def envolvida(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para acessar essa página.", "error")
            return redirect(url_for("login"))
        return visao(*args, **kwargs)

    return envolvida


def admin_obrigatorio(visao):
    @wraps(visao)
    def envolvida(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para acessar o painel.", "error")
            return redirect(url_for("login"))
        if not db.usuario_eh_admin(session["user_id"]):
            flash("Esta página é exclusiva do administrador.", "error")
            return redirect(url_for("home"))
        return visao(*args, **kwargs)

    return envolvida


def token_servico_obrigatorio(visao):
    @wraps(visao)
    def envolvida(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = request.headers.get("X-API-Key", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

        chave_esperada = os.environ.get("BOT_API_KEY", BOT_API_KEY)
        if not token or token != chave_esperada:
            return (
                jsonify({
                    "sucesso": False,
                    "erro": "Não autorizado. Token de serviço inválido ou ausente no header X-API-Key / Authorization.",
                }),
                401,
            )
        return visao(*args, **kwargs)

    return envolvida


def validar_email(email):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is not None


def usuario_atual():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.usuario_por_id(user_id)


def create_app():
    app = Flask(__name__, template_folder=TEMPLATE_DIR)
    app.config["DATABASE"] = db.DB_PATH
    app.config["MAX_CONTENT_LENGTH"] = MAX_ANEXO
    app.secret_key = os.environ.get("SECRET_KEY", "protejaja-cyber-key-producao-2026")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.teardown_appcontext(db.close_connection)

    class ObfuscateServerMiddleware:
        def __init__(self, wsgi_app):
            self.wsgi_app = wsgi_app

        def __call__(self, environ, start_response):
            def custom_start_response(status, response_headers, exc_info=None):
                clean_headers = [
                    (k, v) for k, v in response_headers
                    if k.lower() not in ("server", "x-powered-by")
                ]
                clean_headers.append(("Server", "ProtejaJa-Edge"))
                return start_response(status, clean_headers, exc_info)

            return self.wsgi_app(environ, custom_start_response)

    app.wsgi_app = ObfuscateServerMiddleware(app.wsgi_app)

    with app.app_context():
        db.init_db()

    def get_csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(32)
        return session["_csrf_token"]

    @app.before_request
    def verificar_csrf():
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        if request.path.startswith("/api/"):
            return
        if app.config.get("TESTING") and not request.form.get("csrf_token"):
            return

        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not token or token != session.get("_csrf_token"):
            flash("Sua sessão expirou ou a validação de segurança falhou. Tente novamente.", "error")
            return redirect(request.referrer or url_for("home"))

    @app.after_request
    def headers_seguranca(response):
        response.headers["Server"] = "ProtejaJa-Edge"
        response.headers.pop("X-Powered-By", None)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self';"
        )

        # Compressão Gzip automática para otimização máxima no Lighthouse (payload reduzido em até 85%)
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding.lower() and response.status_code == 200 and not response.direct_passthrough:
            content_type = response.headers.get("Content-Type", "")
            if any(t in content_type for t in ("text/html", "text/css", "application/javascript", "application/json")):
                data = response.get_data()
                if len(data) > 400:
                    compressed = gzip.compress(data, compresslevel=6)
                    response.set_data(compressed)
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = len(compressed)
                    response.headers["Vary"] = "Accept-Encoding"

        return response

    @app.context_processor
    def injetar_contexto():
        css_conteudo = CRITICAL_CSS
        if os.path.exists(CSS_FILE_PATH):
            try:
                with open(CSS_FILE_PATH, "r", encoding="utf-8") as _f:
                    css_conteudo = _f.read()
            except Exception:
                css_conteudo = CRITICAL_CSS
        return {
            "user": usuario_atual(),
            "csrf_token": get_csrf_token,
            "inlined_css": css_conteudo,
            "STATUS_EM_ANALISE_IA": db.STATUS_EM_ANALISE_IA,
            "STATUS_APROVADO": db.STATUS_APROVADO,
            "STATUS_REPROVADO": db.STATUS_REPROVADO,
            "STATUS_ALERTA_REVISAO": db.STATUS_ALERTA_REVISAO,
        }

    # ==========================================================
    # ROTAS PÚBLICAS & INSTITUCIONAIS
    # ==========================================================

    @app.route("/")
    def index():
        return redirect(url_for("home"))

    @app.route("/home")
    def home():
        denuncias_recentes = db.denuncias_aprovadas(limite=3)
        return render_template("home.html", denuncias_recentes=denuncias_recentes)

    @app.route("/diferencial")
    def diferencial():
        return render_template("diferencial.html")

    @app.route("/fato-ou-fake")
    def fato_ou_fake():
        return render_template("fato_ou_fake.html")

    @app.route("/api/v1/checar-fato", methods=["POST"])
    def api_checar_fato():
        texto = ""
        if request.is_json:
            dados = request.get_json(silent=True) or {}
            texto = (dados.get("texto") or "").strip()
        else:
            texto = (request.form.get("texto") or "").strip()

        arquivo_audio = request.files.get("audio")
        if arquivo_audio and arquivo_audio.filename:
            nome_seguro = secure_filename(f"audio_{uuid.uuid4().hex[:8]}_{arquivo_audio.filename}")
            caminho_temp = os.path.join(UPLOAD_DIR, nome_seguro)
            try:
                arquivo_audio.save(caminho_temp)
                if not texto:
                    transcricao = fact_checker.transcrever_audio(caminho_temp)
                    if transcricao:
                        texto = transcricao
            finally:
                try:
                    if os.path.exists(caminho_temp):
                        os.remove(caminho_temp)
                except OSError:
                    pass

        if not texto:
            return jsonify({
                "sucesso": False,
                "erro": "Nenhum áudio ou texto detectado. Fale pelo microfone ou digite o boato para checar."
            }), 400

        resultado = fact_checker.analisar_fato(texto)
        return jsonify(resultado)

    @app.route("/home/<path:filename>")
    def home_static(filename):
        response = send_from_directory(HOME_DIR, filename)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    # ==========================================================
    # SEO / GEO / IAO ENDPOINTS TÉCNICOS
    # ==========================================================

    @app.route("/robots.txt")
    def robots_txt():
        host = request.host_url.rstrip("/")
        conteudo = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin\n"
            "Disallow: /api/\n"
            "Disallow: /uploads/\n\n"
            f"Sitemap: {host}/sitemap.xml\n"
        )
        return Response(conteudo, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        host = request.host_url.rstrip("/")
        paginas = [
            f"{host}/home",
            f"{host}/diferencial",
            f"{host}/denuncias-publicas",
            f"{host}/cadastro",
            f"{host}/login",
        ]
        xml_linhas = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for url in paginas:
            xml_linhas.append("  <url>")
            xml_linhas.append(f"    <loc>{url}</loc>")
            xml_linhas.append("    <changefreq>daily</changefreq>")
            xml_linhas.append("    <priority>0.8</priority>")
            xml_linhas.append("  </url>")
        xml_linhas.append("</urlset>")
        return Response("\n".join(xml_linhas), mimetype="application/xml")

    # ==========================================================
    # AUTENTICAÇÃO E CADASTRO
    # ==========================================================

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        if request.method == "POST":
            nome = (request.form.get("nome") or "").strip()
            sobrenome = (request.form.get("sobrenome") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            data_nascimento = (request.form.get("data_nascimento") or "").strip()
            cidade = (request.form.get("cidade") or "").strip()
            cidade_outra = (request.form.get("cidade_outra") or "").strip()
            if cidade == "Outra Cidade (SP)" and cidade_outra:
                cidade = cidade_outra

            endereco = (request.form.get("endereco") or "").strip()
            senha = request.form.get("senha") or ""
            nome_completo = f"{nome} {sobrenome}".strip()

            if not all([nome, sobrenome, email, data_nascimento, cidade, senha]):
                flash("Preencha todos os campos do cadastro.", "error")
            elif not validar_email(email):
                flash("Informe um e-mail válido.", "error")
            elif len(senha) < 6:
                flash("A senha deve ter no mínimo 6 caracteres.", "error")
            elif contem_ofensa(nome) or contem_ofensa(sobrenome):
                flash("Nome ou sobrenome contêm palavras ofensivas e não podem ser usados.", "error")
            elif contem_ofensa(cidade) or (endereco and contem_ofensa(endereco)):
                flash("Cidade ou endereço contêm palavras ofensivas.", "error")
            elif db.email_cadastrado(email):
                flash("Já existe uma conta com esse e-mail.", "error")
            else:
                senha_hash = generate_password_hash(senha)
                db.criar_usuario(
                    nome_completo,
                    email,
                    data_nascimento,
                    cidade,
                    endereco,
                    senha_hash,
                )
                flash("Conta criada com sucesso! Faça login para continuar.", "success")
                return redirect(url_for("login"))

        return render_template("cadastro.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            senha = request.form.get("senha") or ""

            usuario = db.usuario_por_email(email) if email else None

            if usuario and check_password_hash(usuario["senha_hash"], senha):
                session.clear()
                session["user_id"] = usuario["id"]
                flash(f"Acesso liberado. Bem-vindo(a), {usuario['nome']}!", "success")
                return redirect(url_for("home"))

            flash("E-mail ou senha incorretos.", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Sessão finalizada com segurança.", "success")
        return redirect(url_for("home"))

    @app.route("/recuperar", methods=["GET", "POST"])
    def recuperar():
        resultado = None

        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            data_nascimento = (request.form.get("data_nascimento") or "").strip()

            usuario = db.usuario_por_email(email) if email else None

            if not usuario or usuario["data_nascimento"] != data_nascimento:
                flash("Dados não conferem com nenhuma conta cadastrada.", "error")
            else:
                temporaria = secrets.token_urlsafe(8)
                db.atualizar_senha(usuario["id"], generate_password_hash(temporaria))
                resultado = (usuario["nome"], temporaria)

        return render_template("recuperar.html", senha_temporaria=resultado)

    # ==========================================================
    # DENÚNCIAS & TERMO DE RESPONSABILIDADE LEGAL
    # ==========================================================

    @app.route("/denuncias", methods=["GET", "POST"])
    @login_obrigatorio
    def denuncias():
        usuario = db.usuario_por_id(session["user_id"])

        if request.method == "POST":
            denunciado = (request.form.get("denunciado") or "").strip()
            cidade = (request.form.get("cidade") or "Araraquara").strip()
            cidade_outra = (request.form.get("cidade_outra") or "").strip()
            if cidade == "Outra Cidade (SP)" and cidade_outra:
                cidade = cidade_outra
            bairro = (request.form.get("bairro") or "Centro").strip()

            assunto = (request.form.get("assunto") or "").strip()
            categoria = (request.form.get("categoria") or "Geral").strip()
            descricao = (request.form.get("descricao") or "").strip()
            termo_aceito = request.form.get("termo_responsabilidade")
            anexo = request.files.get("anexo")

            if not termo_aceito:
                flash("É obrigatório ler e concordar com o Termo de Declaração e Responsabilidade Legal.", "error")
            elif not denunciado:
                flash("Informe quem você está denunciando (estabelecimento, empresa ou pessoa).", "error")
            elif not cidade:
                flash("Informe a cidade onde ocorreu o fato.", "error")
            elif not bairro:
                flash("Informe o bairro da unidade/estabelecimento denunciado.", "error")
            elif not assunto:
                flash("Informe sobre o que você está denunciando.", "error")
            elif not descricao:
                flash("Descreva a denúncia antes de enviar.", "error")
            elif contem_ofensa(denunciado):
                flash("O nome informado contém termos de baixo calão ou ofensas. Por favor, revise para manter o respeito.", "error")
            elif contem_ofensa(cidade) or contem_ofensa(bairro):
                flash("A cidade ou bairro contêm termos de baixo calão. Por favor, informe dados válidos.", "error")
            elif contem_ofensa(assunto):
                flash("O assunto contém palavras de baixo calão. O ProtejaJá preza pelo respeito e não aceita ofensas.", "error")
            elif contem_ofensa(descricao):
                flash("A descrição contém termos de baixo calão ou ofensas. Mantenha o relato respeitoso e focado nos fatos para que sua denúncia seja aceita.", "error")
            else:
                nome_anexo = None
                anexo_invalido = False

                if anexo and anexo.filename:
                    nome_seguro = secure_filename(anexo.filename)
                    if not arquivo_permitido(anexo.filename) or not nome_seguro:
                        anexo_invalido = True
                        flash("Foto ou anexo não recomendado. Envie apenas fotos nítidas do produto, local, cupom fiscal (JPG, PNG, WEBP) ou PDF/vídeo até 5 MB.", "error")
                    else:
                        ext = nome_seguro.rsplit(".", 1)[1].lower() if "." in nome_seguro else "bin"
                        nome_anexo = f"{uuid.uuid4().hex[:12]}_{nome_seguro}"
                        anexo.save(os.path.join(UPLOAD_DIR, nome_anexo))

                if not anexo_invalido:
                    db.criar_denuncia(
                        usuario["id"],
                        sanitizar(denunciado),
                        sanitizar(assunto),
                        categoria,
                        sanitizar(descricao),
                        nome_anexo,
                        termo_aceito=1,
                        cidade=sanitizar(cidade),
                        bairro=sanitizar(bairro),
                    )
                    flash("Denúncia enviada com sucesso! Ela foi para análise e será postada em até 24 horas se seguir as diretrizes da comunidade.", "success")

        denuncias_lista = db.denuncias_do_usuario(usuario["id"])
        return render_template("denuncias.html", denuncias=denuncias_lista)

    @app.route("/denuncias-publicas")
    def denuncias_publicas():
        categoria_filtro = request.args.get("categoria", "").strip()
        cidade_filtro = request.args.get("cidade", "").strip()
        busca = request.args.get("q", "").strip()
        denuncias = db.denuncias_aprovadas(limite=20)

        if categoria_filtro:
            denuncias = [d for d in denuncias if d["categoria"].lower() == categoria_filtro.lower()]
        if cidade_filtro:
            denuncias = [d for d in denuncias if d["cidade"].lower() == cidade_filtro.lower()]
        if busca:
            termo = busca.lower()
            denuncias = [
                d for d in denuncias
                if termo in d["denunciado"].lower()
                or termo in d["assunto"].lower()
                or termo in d["descricao"].lower()
                or termo in d["bairro"].lower()
            ]

        return render_template(
            "denuncias_publicas.html",
            denuncias=denuncias,
            categoria_ativa=categoria_filtro,
            cidade_ativa=cidade_filtro,
            busca=busca,
        )

    @app.route("/denuncias/<int:denuncia_id>")
    @login_obrigatorio
    def ver_denuncia(denuncia_id):
        denuncia = db.denuncia_do_usuario(session["user_id"], denuncia_id)
        if denuncia is None:
            flash("Denúncia não encontrada ou não pertence à sua conta.", "error")
            return redirect(url_for("denuncias"))
        return render_template("ver_denuncia.html", denuncia=denuncia)

    @app.route("/excluir-conta", methods=["GET", "POST"])
    @login_obrigatorio
    def excluir_conta():
        user_id = session["user_id"]
        usuario = db.usuario_por_id(user_id)

        if request.method == "POST":
            senha = request.form.get("senha") or ""
            if not check_password_hash(usuario["senha_hash"], senha):
                flash("Senha incorreta. A exclusão foi cancelada.", "error")
            else:
                for linha in db.anexos_do_usuario(user_id):
                    caminho = os.path.join(UPLOAD_DIR, linha["anexo"])
                    if os.path.exists(caminho):
                        try:
                            os.remove(caminho)
                        except OSError:
                            pass
                db.apagar_conta_completa(user_id)
                session.clear()
                flash("Sua conta e todos os seus dados foram permanentemente expurgados.", "success")
                return redirect(url_for("home"))

        return render_template("excluir_conta.html")

    # ==========================================================
    # PAINEL ADMINISTRATIVO & MODERAÇÃO
    # ==========================================================

    @app.route("/admin")
    @admin_obrigatorio
    def painel_admin():
        filtro = request.args.get("status")
        if filtro and filtro not in db.STATUS_VALIDOS:
            filtro = None

        denuncias = db.todas_denuncias(filtro_status=filtro)
        metricas = db.contadores_metricas()
        return render_template(
            "admin.html",
            denuncias=denuncias,
            metricas=metricas,
            filtro_ativo=filtro,
        )

    @app.route("/admin/moderar/<int:denuncia_id>", methods=["POST", "GET"])
    @admin_obrigatorio
    def moderar_denuncia(denuncia_id):
        novo_status = request.form.get("status") or request.args.get("status")
        if novo_status not in db.STATUS_VALIDOS:
            flash("Status de moderação inválido.", "error")
            return redirect(url_for("painel_admin"))

        admin_id = session.get("user_id")
        db.atualizar_status_denuncia(denuncia_id, novo_status, admin_id=admin_id)

        mensagens = {
            db.STATUS_APROVADO: "Denúncia APROVADA e disponibilizada no feed público.",
            db.STATUS_REPROVADO: "Denúncia REPROVADA e arquivada.",
            db.STATUS_ALERTA_REVISAO: "Denúncia mantida sob ALERTA para análise técnica aprofundada.",
            db.STATUS_EM_ANALISE_IA: "Denúncia reenviada para o pipeline de auditoria automatizada.",
        }
        flash(mensagens.get(novo_status, "Status atualizado com sucesso."), "success")
        return redirect(request.referrer or url_for("painel_admin"))

    @app.route("/admin/aprovar/<int:denuncia_id>", methods=["GET", "POST"])
    @admin_obrigatorio
    def aprovar_denuncia(denuncia_id):
        return moderar_denuncia(denuncia_id)

    @app.route("/admin/rejeitar/<int:denuncia_id>", methods=["GET", "POST"])
    @admin_obrigatorio
    def rejeitar_denuncia(denuncia_id):
        return moderar_denuncia(denuncia_id)

    # ==========================================================
    # API v1 REST PARA TRIAGEM IA / BOT LOCAL & TICKER
    # ==========================================================

    @app.route("/api/v1/noticias")
    def api_noticias():
        """Fornece dados estruturados para o Sticky Persistent Footer Ticker."""
        aprovadas = db.denuncias_aprovadas(limite=5)
        noticias = []
        for d in aprovadas:
            noticias.append({
                "id": d["id"],
                "tag": d["categoria"].upper(),
                "titulo": f"{d['denunciado']} ({d['bairro']}, {d['cidade']}): {d['assunto']}",
                "tempo": d["criado_em"],
            })

        if not noticias:
            noticias = [
                {
                    "id": "sys-1",
                    "tag": "RADAR",
                    "titulo": "ProtejaJá Operacional // Denúncias comunitárias verificadas e postadas em até 24h",
                    "tempo": "Tempo Real",
                },
                {
                    "id": "sys-2",
                    "tag": "EMERGÊNCIA",
                    "titulo": "Telefones Úteis: PM 190, Bombeiros 193, SAMU 192 e Procon 151",
                    "tempo": "24 Horas",
                },
                {
                    "id": "sys-3",
                    "tag": "CIDADANIA",
                    "titulo": "Região de Araraquara e Ribeirão Preto: canal oficial de proteção comunitária",
                    "tempo": "Ativo",
                },
            ]

        return jsonify({"sucesso": True, "total": len(noticias), "noticias": noticias})

    @app.route("/api/v1/denuncias/pendentes", methods=["GET"])
    @token_servico_obrigatorio
    def api_denuncias_pendentes():
        """Consumido pelo bot local para triagem automatizada com IA."""
        limite = request.args.get("limite", default=20, type=int)
        pendentes = db.denuncias_pendentes_ia(limite=limite)

        lista = []
        for p in pendentes:
            anexo_url = (
                url_for("uploads", filename=p["anexo"], _external=True)
                if p["anexo"]
                else None
            )
            lista.append({
                "id": p["id"],
                "user_id": p["user_id"],
                "denunciado": p["denunciado"],
                "cidade": p["cidade"],
                "bairro": p["bairro"],
                "assunto": p["assunto"],
                "categoria": p["categoria"],
                "descricao": p["descricao"],
                "anexo": p["anexo"],
                "anexo_url": anexo_url,
                "status": p["status"],
                "termo_aceito": bool(p["termo_aceito"]),
                "criado_em": p["criado_em"],
            })

        return jsonify({
            "sucesso": True,
            "total_pendentes": len(lista),
            "denuncias": lista,
        })

    @app.route("/api/v1/denuncias/<int:denuncia_id>/triagem", methods=["PATCH"])
    @token_servico_obrigatorio
    def api_triagem_denuncia(denuncia_id):
        """Atualiza a denúncia com o parecer, score e justificativa da IA."""
        dados = request.get_json(silent=True) or {}
        novo_status = dados.get("status")
        score_confianca = dados.get("score_confianca")
        justificativa_ia = dados.get("justificativa_ia")

        status_permitidos_ia = {
            db.STATUS_APROVADO,
            db.STATUS_REPROVADO,
            db.STATUS_ALERTA_REVISAO,
        }

        if not novo_status or novo_status not in status_permitidos_ia:
            return (
                jsonify({
                    "sucesso": False,
                    "erro": f"Status inválido. Escolha um entre: {list(status_permitidos_ia)}",
                }),
                400,
            )

        if score_confianca is not None:
            try:
                score_confianca = float(score_confianca)
                if not (0.0 <= score_confianca <= 1.0):
                    raise ValueError()
            except (ValueError, TypeError):
                return (
                    jsonify({
                        "sucesso": False,
                        "erro": "score_confianca deve ser um número decimal entre 0.0 e 1.0",
                    }),
                    400,
                )

        denuncia = db.denuncia_por_id_geral(denuncia_id)
        if not denuncia:
            return jsonify({"sucesso": False, "erro": "Denúncia não encontrada."}), 404

        db.atualizar_triagem_ia(
            denuncia_id=denuncia_id,
            novo_status=novo_status,
            score_confianca=score_confianca,
            justificativa_ia=justificativa_ia,
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Triagem de IA registrada com sucesso.",
            "denuncia_id": denuncia_id,
            "status_atual": novo_status,
            "score_confianca": score_confianca,
            "justificativa_ia": justificativa_ia,
        })

    return app