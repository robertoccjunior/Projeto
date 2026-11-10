import os
import sqlite3
from flask import g, has_app_context
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "db", "app.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "backend", "uploads")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@protejaja.com")
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "admin123")

# Status oficiais do pipeline de moderação e IA
STATUS_EM_ANALISE_IA = "EM_ANALISE_IA"
STATUS_APROVADO = "APROVADO"
STATUS_REPROVADO = "REPROVADO"
STATUS_ALERTA_REVISAO = "ALERTA_REVISAO_MANUAL"

STATUS_VALIDOS = {
    STATUS_EM_ANALISE_IA,
    STATUS_APROVADO,
    STATUS_REPROVADO,
    STATUS_ALERTA_REVISAO,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    data_nascimento TEXT NOT NULL,
    cidade TEXT NOT NULL,
    endereco TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS reports (
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
"""


def get_connection():
    if has_app_context():
        if "db_conn" not in g:
            g.db_conn = sqlite3.connect(DB_PATH)
            g.db_conn.row_factory = sqlite3.Row
            g.db_conn.execute("PRAGMA foreign_keys = ON")
        return g.db_conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def close_connection(exception=None):
    if has_app_context() and "db_conn" in g:
        conn = g.pop("db_conn", None)
        if conn is not None:
            conn.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    colunas_reports = {
        r[1] for r in conn.execute("PRAGMA table_info(reports)").fetchall()
    }
    if "assunto" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN assunto TEXT NOT NULL DEFAULT 'Sem assunto'")
    if "denunciado" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN denunciado TEXT NOT NULL DEFAULT ''")
    if "status" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN status TEXT NOT NULL DEFAULT 'EM_ANALISE_IA'")
    if "score_confianca" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN score_confianca REAL DEFAULT NULL")
    if "justificativa_ia" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN justificativa_ia TEXT DEFAULT NULL")
    if "data_analise_ia" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN data_analise_ia TEXT DEFAULT NULL")
    if "analisado_por_admin_id" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN analisado_por_admin_id INTEGER DEFAULT NULL")
    if "termo_aceito" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN termo_aceito INTEGER NOT NULL DEFAULT 1")
    if "data_aceite_termo" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN data_aceite_termo TEXT DEFAULT NULL")
    if "cidade" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN cidade TEXT NOT NULL DEFAULT 'Araraquara'")
    if "bairro" not in colunas_reports:
        conn.execute("ALTER TABLE reports ADD COLUMN bairro TEXT NOT NULL DEFAULT 'Centro'")

    # Migração e normalização de status legados
    conn.execute("UPDATE reports SET status = ? WHERE status IN ('pendente', 'PENDENTE')", (STATUS_EM_ANALISE_IA,))
    conn.execute("UPDATE reports SET status = ? WHERE status IN ('aprovada', 'APROVADA')", (STATUS_APROVADO,))
    conn.execute("UPDATE reports SET status = ? WHERE status IN ('rejeitada', 'REJEITADA')", (STATUS_REPROVADO,))

    colunas_users = {
        r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "is_admin" not in colunas_users:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    admin = conn.execute(
        "SELECT id FROM users WHERE email = ? COLLATE NOCASE", (ADMIN_EMAIL,)
    ).fetchone()
    if admin is None:
        conn.execute(
            "INSERT INTO users (nome, email, data_nascimento, cidade, endereco, senha_hash, is_admin) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (
                "Administrador",
                ADMIN_EMAIL,
                "01/01/2000",
                "Matão",
                "Central",
                generate_password_hash(ADMIN_SENHA),
            ),
        )
    else:
        conn.execute("UPDATE users SET is_admin = 1 WHERE email = ? COLLATE NOCASE", (ADMIN_EMAIL,))

    conn.commit()
    conn.close()


def email_cadastrado(email):
    conn = get_connection()
    row = conn.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
    if not has_app_context():
        conn.close()
    return row is not None


def criar_usuario(nome, email, data_nascimento, cidade, endereco="", senha_hash=""):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO users (nome, email, data_nascimento, cidade, endereco, senha_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (nome, email, data_nascimento, cidade, endereco or "", senha_hash),
    )
    conn.commit()
    user_id = cur.lastrowid
    if not has_app_context():
        conn.close()
    return user_id


def usuario_por_email(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, nome, email, data_nascimento, cidade, endereco, senha_hash, criado_em, is_admin "
        "FROM users WHERE email = ? COLLATE NOCASE",
        (email,),
    ).fetchone()
    if not has_app_context():
        conn.close()
    return row


def usuario_por_id(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, nome, email, data_nascimento, cidade, endereco, senha_hash, criado_em, is_admin "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not has_app_context():
        conn.close()
    return row


def atualizar_senha(user_id, senha_hash):
    conn = get_connection()
    conn.execute("UPDATE users SET senha_hash = ? WHERE id = ?", (senha_hash, user_id))
    conn.commit()
    if not has_app_context():
        conn.close()


def criar_denuncia(user_id, denunciado, assunto, categoria, descricao, anexo, termo_aceito=1, cidade="Araraquara", bairro="Centro"):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO reports (user_id, denunciado, assunto, categoria, descricao, anexo, status, termo_aceito, data_aceite_termo, cidade, bairro) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?)",
        (user_id, denunciado, assunto, categoria, descricao, anexo, STATUS_EM_ANALISE_IA, int(termo_aceito), cidade, bairro),
    )
    conn.commit()
    report_id = cur.lastrowid
    if not has_app_context():
        conn.close()
    return report_id


def denuncia_do_usuario(user_id, denuncia_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, denunciado, assunto, categoria, descricao, anexo, status, score_confianca, justificativa_ia, data_analise_ia, termo_aceito, criado_em, cidade, bairro "
        "FROM reports WHERE id = ? AND user_id = ?",
        (denuncia_id, user_id),
    ).fetchone()
    if not has_app_context():
        conn.close()
    return row


def denuncias_do_usuario(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, denunciado, assunto, categoria, descricao, anexo, status, score_confianca, justificativa_ia, data_analise_ia, criado_em, cidade, bairro "
        "FROM reports WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    if not has_app_context():
        conn.close()
    return rows


def anexos_do_usuario(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT anexo FROM reports WHERE user_id = ? AND anexo IS NOT NULL",
        (user_id,),
    ).fetchall()
    if not has_app_context():
        conn.close()
    return rows


def apagar_conta_completa(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM reports WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    if not has_app_context():
        conn.close()


def promover_admin(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
    conn.commit()
    if not has_app_context():
        conn.close()


def usuario_eh_admin(user_id):
    conn = get_connection()
    row = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not has_app_context():
        conn.close()
    return bool(row and row["is_admin"])


def todas_denuncias(filtro_status=None):
    conn = get_connection()
    if filtro_status:
        rows = conn.execute(
            "SELECT r.*, u.nome AS autor_nome, u.email AS autor_email "
            "FROM reports r "
            "JOIN users u ON r.user_id = u.id "
            "WHERE r.status = ? "
            "ORDER BY r.id DESC",
            (filtro_status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT r.*, u.nome AS autor_nome, u.email AS autor_email "
            "FROM reports r "
            "JOIN users u ON r.user_id = u.id "
            "ORDER BY r.id DESC",
        ).fetchall()
    if not has_app_context():
        conn.close()
    return rows


def denuncia_por_id_geral(denuncia_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT r.*, u.nome AS autor_nome, u.email AS autor_email "
        "FROM reports r "
        "JOIN users u ON r.user_id = u.id "
        "WHERE r.id = ?",
        (denuncia_id,),
    ).fetchone()
    if not has_app_context():
        conn.close()
    return row


def atualizar_status_denuncia(denuncia_id, novo_status, admin_id=None):
    conn = get_connection()
    if admin_id:
        conn.execute(
            "UPDATE reports SET status = ?, analisado_por_admin_id = ? WHERE id = ?",
            (novo_status, admin_id, denuncia_id),
        )
    else:
        conn.execute("UPDATE reports SET status = ? WHERE id = ?", (novo_status, denuncia_id))
    conn.commit()
    if not has_app_context():
        conn.close()


def denuncias_pendentes_ia(limite=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, user_id, denunciado, assunto, categoria, descricao, anexo, status, criado_em, termo_aceito, cidade, bairro "
        "FROM reports "
        "WHERE status = ? "
        "ORDER BY id ASC LIMIT ?",
        (STATUS_EM_ANALISE_IA, limite),
    ).fetchall()
    if not has_app_context():
        conn.close()
    return rows


def atualizar_triagem_ia(denuncia_id, novo_status, score_confianca=None, justificativa_ia=None):
    if novo_status not in STATUS_VALIDOS:
        raise ValueError(f"Status inválido: {novo_status}")
    conn = get_connection()
    conn.execute(
        "UPDATE reports "
        "SET status = ?, score_confianca = ?, justificativa_ia = ?, data_analise_ia = datetime('now', 'localtime') "
        "WHERE id = ?",
        (novo_status, score_confianca, justificativa_ia, denuncia_id),
    )
    conn.commit()
    if not has_app_context():
        conn.close()


def denuncias_aprovadas(limite=100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, denunciado, assunto, categoria, descricao, anexo, criado_em, cidade, bairro "
        "FROM reports WHERE status = ? ORDER BY id DESC LIMIT ?",
        (STATUS_APROVADO, limite),
    ).fetchall()
    if not has_app_context():
        conn.close()
    return rows


def contadores_metricas():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]
    em_analise = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE status = ?", (STATUS_EM_ANALISE_IA,)).fetchone()["c"]
    alerta = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE status = ?", (STATUS_ALERTA_REVISAO,)).fetchone()["c"]
    aprovados = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE status = ?", (STATUS_APROVADO,)).fetchone()["c"]
    reprovados = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE status = ?", (STATUS_REPROVADO,)).fetchone()["c"]
    if not has_app_context():
        conn.close()
    return {
        "total": total,
        "em_analise_ia": em_analise,
        "alerta_revisao": alerta,
        "aprovados": aprovados,
        "reprovados": reprovados,
    }