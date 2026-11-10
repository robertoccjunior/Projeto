"""
Módulo de Verificação de Fatos com Agentic Web Search em Tempo Real // ProtejaJá
Substitui RAG tradicional por busca ativa na web e validação com Filtro de Autoridade.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Literal, Optional, TypedDict

logger = logging.getLogger("protejaja.agentic_checker")

# ---------------------------------------------------------------------------
# Tipagens Estritas (PEP 589 / TypedDict)
# ---------------------------------------------------------------------------

StatusVerificacao = Literal["fato", "fake", "alerta", "inconclusivo"]


class FonteRecomendada(TypedDict):
    nome: str
    url: Optional[str]


class ResultadoVerificacao(TypedDict):
    status: StatusVerificacao
    confianca: int
    parecer: str
    fonte_recomendada: FonteRecomendada


class ItemBusca(TypedDict):
    titulo: str
    url: str
    trecho: str
    portal: str


# ---------------------------------------------------------------------------
# Constantes & Prompt do Sistema (Filtro de Autoridade Restrito)
# ---------------------------------------------------------------------------

PROMPT_SISTEMA = (
    "Você é um auditor de fatos específicos. Analise a afirmação do usuário baseando-se "
    "EXCLUSIVAMENTE nos excertos de pesquisa web fornecidos. Regra de Ouro: Só classifique como "
    "FATO ou FAKE se a informação for validada ou desmentida por portais de jornalismo de alta "
    "referência (ex: Reuters, G1, UOL) ou sites governamentais/oficiais. Se os resultados da pesquisa "
    "não falam exatamente sobre o tema, ou se a afirmação for um boato local sem cobertura da imprensa, "
    "NÃO invente justificativas, classifique obrigatoriamente como INCONCLUSIVO."
)

RESULTADO_INCONCLUSIVO_PADRAO: ResultadoVerificacao = {
    "status": "inconclusivo",
    "confianca": 0,
    "parecer": "Não foi possível verificar a afirmação com fontes oficiais de imprensa no momento.",
    "fonte_recomendada": {
        "nome": "Inexistente",
        "url": None,
    },
}

PORTAIS_AUTORIDADE = [
    (r"g1\.globo\.com", "G1"),
    (r"reuters\.com", "Reuters"),
    (r"uol\.com\.br", "UOL"),
    (r"estadao\.com\.br", "Estadão Verifica"),
    (r"folha\.uol\.com\.br", "Folha de S.Paulo"),
    (r"bbc\.com", "BBC News Brasil"),
    (r"aosfatos\.org", "Aos Fatos"),
    (r"piaui\.folha\.uol\.com\.br/lupa", "Agência Lupa"),
    (r"lupa\.news", "Agência Lupa"),
    (r"cnnbrasil\.com\.br", "CNN Brasil"),
    (r"agenciabrasil\.ebc\.com\.br", "Agência Brasil"),
    (r"\.gov\.br", "Portal Governamental Oficial"),
    (r"\.jus\.br", "Poder Judiciário Oficial"),
    (r"\.leg\.br", "Congresso Nacional Oficial"),
    (r"anvisa\.gov\.br", "Anvisa (Oficial)"),
    (r"bcb\.gov\.br", "Banco Central do Brasil (Oficial)"),
    (r"tse\.jus\.br", "Tribunal Superior Eleitoral (Oficial)"),
    (r"stf\.jus\.br", "Supremo Tribunal Federal (Oficial)"),
]


def identificar_portal_autoridade(url: str, titulo: str = "") -> Optional[str]:
    """Identifica se a URL ou título pertence a um veículo de imprensa de referência ou órgão oficial."""
    url_lower = (url or "").lower()
    for padrao, nome in PORTAIS_AUTORIDADE:
        if re.search(padrao, url_lower):
            return nome

    titulo_lower = (titulo or "").lower()
    if " | g1" in titulo_lower or "g1 -" in titulo_lower:
        return "G1"
    if "reuters" in titulo_lower:
        return "Reuters"
    if "uol confere" in titulo_lower or " | uol" in titulo_lower:
        return "UOL"
    if "aos fatos" in titulo_lower:
        return "Aos Fatos"
    if "agência lupa" in titulo_lower:
        return "Agência Lupa"

    return None


# ---------------------------------------------------------------------------
# 1. Integração de Busca Web (DuckDuckGo, Tavily ou Serper)
# ---------------------------------------------------------------------------

def buscar_web(afirmacao: str, max_resultados: int = 5) -> List[ItemBusca]:
    """
    Executa busca na web recuperando os excertos mais relevantes.
    Prioriza APIs dedicadas caso configuradas em variáveis de ambiente,
    com fallback transparente para a biblioteca ddgs / duckduckgo_search.
    """
    termo_busca = afirmacao.strip()
    if not termo_busca:
        return []

    # 1.1 Tentativa via Tavily API (se configurado)
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            req_data = json.dumps({
                "api_key": tavily_key,
                "query": termo_busca,
                "search_depth": "advanced",
                "max_results": max_resultados,
                "include_domains": ["g1.globo.com", "uol.com.br", "reuters.com", "gov.br", "aosfatos.org"]
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                resultados = []
                for item in data.get("results", [])[:max_resultados]:
                    url = item.get("url", "")
                    titulo = item.get("title", "")
                    portal = identificar_portal_autoridade(url, titulo) or "Web"
                    resultados.append({
                        "titulo": titulo,
                        "url": url,
                        "trecho": item.get("content", ""),
                        "portal": portal
                    })
                if resultados:
                    return resultados
        except Exception as e:
            logger.warning("Falha na busca Tavily, recorrendo a ddgs: %s", e)

    # 1.2 Tentativa via Serper API (se configurado)
    serper_key = os.environ.get("SERPER_API_KEY")
    if serper_key:
        try:
            req_data = json.dumps({
                "q": f"{termo_busca} brasil noticia fato ou fake",
                "gl": "br",
                "hl": "pt-br",
                "num": max_resultados
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://google.serper.dev/search",
                data=req_data,
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                resultados = []
                for item in data.get("organic", [])[:max_resultados]:
                    url = item.get("link", "")
                    titulo = item.get("title", "")
                    portal = identificar_portal_autoridade(url, titulo) or "Web"
                    resultados.append({
                        "titulo": titulo,
                        "url": url,
                        "trecho": item.get("snippet", ""),
                        "portal": portal
                    })
                if resultados:
                    return resultados
        except Exception as e:
            logger.warning("Falha na busca Serper, recorrendo a ddgs: %s", e)

    # 1.3 DuckDuckGo Search (biblioteca ddgs nativa)
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore

        resultados: List[ItemBusca] = []
        with DDGS() as ddgs:
            # Busca geral com contexto informativo em português
            itens = list(ddgs.text(
                f"{termo_busca} fato fake checagem",
                max_results=max_resultados,
                region="br-pt"
            ))

            # Se não retornar resultados com o termo refinado, tenta busca direta
            if not itens:
                itens = list(ddgs.text(termo_busca, max_results=max_resultados))

            for r in itens:
                url = r.get("href") or r.get("url") or ""
                titulo = r.get("title") or ""
                trecho = r.get("body") or r.get("snippet") or ""
                portal = identificar_portal_autoridade(url, titulo) or "Veículo Web"
                resultados.append({
                    "titulo": titulo,
                    "url": url,
                    "trecho": trecho,
                    "portal": portal
                })

        return resultados[:max_resultados]
    except Exception as e:
        logger.error("Erro na busca DuckDuckGo: %s", e)
        return []


# ---------------------------------------------------------------------------
# 2 & 3. Consulta ao LLM com Prompt do Sistema & Retorno Estruturado JSON
# ---------------------------------------------------------------------------

def _executar_chamada_llm_api(prompt_sistema: str, prompt_usuario: str) -> Optional[str]:
    """
    Executa chamada HTTP a um LLM compatível com a API OpenAI (OpenAI, Groq, Ollama, OpenRouter).
    Usa a biblioteca padrão urllib (sem dependências pesadas externas).
    """
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1"
    modelo = os.environ.get("LLM_MODEL")

    if not api_key:
        # Verifica se há Ollama local ativo (ex: http://localhost:11434/v1)
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            teste_req = urllib.request.Request(f"{ollama_url}/api/tags", headers={"User-Agent": "ProtejaJa"})
            with urllib.request.urlopen(teste_req, timeout=1.5):
                api_base = f"{ollama_url}/v1"
                api_key = "ollama"
                if not modelo:
                    modelo = "llama3"
        except Exception:
            return None

    if not modelo:
        if "groq.com" in api_base or os.environ.get("GROQ_API_KEY"):
            modelo = "llama-3.3-70b-versatile"
            api_base = "https://api.groq.com/openai/v1"
        else:
            modelo = "gpt-4o-mini"

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }

    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ProtejaJa-AgenticSearch/2.0"
        }
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        corpo = json.loads(resp.read().decode("utf-8"))
        escolhas = corpo.get("choices", [])
        if escolhas:
            return escolhas[0].get("message", {}).get("content")

    return None


def _calcular_relevancia_tema(afirmacao: str, titulo: str, trecho: str) -> bool:
    """Verifica se o excerto realmente fala sobre o tema específico da afirmação."""
    stop_words = {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não",
        "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi",
        "ao", "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito",
        "fato", "fake", "boato", "noticia", "notícia", "verdade", "checagem", "sobre"
    }
    palavras = [
        p.lower() for p in re.findall(r"\b\w{3,}\b", afirmacao)
        if p.lower() not in stop_words
    ]
    if not palavras:
        return True

    texto_item = f"{titulo} {trecho}".lower()
    matches = sum(1 for p in palavras if p in texto_item)
    limiar = max(1, min(2, len(palavras)))
    return matches >= limiar


def _auditar_excertos_regra_de_ouro(afirmacao: str, excertos: List[ItemBusca]) -> ResultadoVerificacao:
    """
    Implementação da 'Regra de Ouro' do Filtro de Autoridade.
    Avalia estritamente se há confirmação ou desmentido por portais de referência (Reuters, G1, UOL, Gov).
    Se não houver cobertura da grande imprensa ou se for boato local, retorna obrigatoriamente INCONCLUSIVO.
    """
    if not excertos:
        return RESULTADO_INCONCLUSIVO_PADRAO

    # Filtra apenas excertos originários de portais com autoridade reconhecida E que falem do tema
    excertos_autorizados: List[ItemBusca] = [
        item for item in excertos
        if identificar_portal_autoridade(item["url"], item["titulo"]) is not None
        and _calcular_relevancia_tema(afirmacao, item["titulo"], item["trecho"])
    ]

    # Se nenhum dos 5 resultados pertence à grande imprensa sobre o tema específico, é inconclusivo
    if not excertos_autorizados:
        return {
            "status": "inconclusivo",
            "confianca": 0,
            "parecer": (
                "A afirmação não possui cobertura confirmada por portais de jornalismo de alta referência "
                "(ex: Reuters, G1, UOL) nem por órgãos governamentais/oficiais sobre este tema específico. "
                "Classificado obrigatoriamente como inconclusivo."
            ),
            "fonte_recomendada": {
                "nome": "Inexistente",
                "url": None
            }
        }

    # Analisa termos de desmentido em portais de alta referência
    padroes_desmentido = [
        r"\b(é falso|e falso|falso|fake|boato|golpe|desmente|desmentido|não é verdade|nao e verdade|inconstitucional|engana|farsa)\b"
    ]
    padroes_confirmacao = [
        r"\b(é verdade|e verdade|fato|confirma|confirmado|oficializa|anvisa aprova|sanciona|sancionou|legítimo|legitimo)\b"
    ]

    for item in excertos_autorizados:
        texto_completo = f"{item['titulo']} {item['trecho']}".lower()
        portal = item["portal"]

        # 1. Desmentido formal localizado
        if any(re.search(p, texto_completo, re.IGNORECASE) for p in padroes_desmentido):
            return {
                "status": "fake",
                "confianca": 98,
                "parecer": f"A alegação foi formalmente apurada e desmentida por {portal}: '{item['titulo']}'.",
                "fonte_recomendada": {
                    "nome": portal,
                    "url": item["url"]
                }
            }

        # 2. Confirmação formal localizada
        if any(re.search(p, texto_completo, re.IGNORECASE) for p in padroes_confirmacao):
            return {
                "status": "fato",
                "confianca": 95,
                "parecer": f"A informação foi verificada e validada com respaldo de {portal}: '{item['titulo']}'.",
                "fonte_recomendada": {
                    "nome": portal,
                    "url": item["url"]
                }
            }

    # Se há menção em portal de referência, mas sem veredito binário claro (ex: juízo de valor / em apuração)
    primeiro_autorizado = excertos_autorizados[0]
    return {
        "status": "alerta",
        "confianca": 70,
        "parecer": (
            f"O tema foi noticiado por {primeiro_autorizado['portal']}, mas a alegação envolve juízo de valor "
            "ou apuração factual em andamento. Recomenda-se conferir a íntegra da matéria."
        ),
        "fonte_recomendada": {
            "nome": primeiro_autorizado["portal"],
            "url": primeiro_autorizado["url"]
        }
    }


def _parse_resposta_json(conteudo: str) -> Optional[ResultadoVerificacao]:
    """Valida e extrai estritamente o formato JSON exigido pelo contrato."""
    if not conteudo:
        return None

    # Limpeza de markdown code block ```json ... ``` caso o LLM inclua
    conteudo_limpo = conteudo.strip()
    match_code = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", conteudo_limpo, re.DOTALL)
    if match_code:
        conteudo_limpo = match_code.group(1).strip()
    else:
        match_braces = re.search(r"(\{.*\})", conteudo_limpo, re.DOTALL)
        if match_braces:
            conteudo_limpo = match_braces.group(1).strip()

    try:
        dados = json.loads(conteudo_limpo)
        status = str(dados.get("status", "")).strip().lower()
        if status not in ("fato", "fake", "alerta", "inconclusivo"):
            return None

        confianca = int(dados.get("confianca", 0))
        parecer = str(dados.get("parecer", "")).strip()

        fonte_raw = dados.get("fonte_recomendada") or {}
        fonte_nome = str(fonte_raw.get("nome", "Inexistente")).strip()
        fonte_url = fonte_raw.get("url")
        if fonte_url:
            fonte_url = str(fonte_url).strip()

        return {
            "status": status,  # type: ignore[return-value]
            "confianca": max(0, min(100, confianca)),
            "parecer": parecer or "Verificação concluída.",
            "fonte_recomendada": {
                "nome": fonte_nome or "Inexistente",
                "url": fonte_url if fonte_url and fonte_url.startswith("http") else None
            }
        }
    except Exception as e:
        logger.warning("Falha ao parsear JSON do LLM: %s | Conteúdo: %s", e, conteudo[:120])
        return None


# ---------------------------------------------------------------------------
# 4. Pipeline Principal com Tratamento de Exceções Robusto
# ---------------------------------------------------------------------------

def processar_entrada_usuario(afirmacao: str) -> ResultadoVerificacao:
    """
    Pipeline completo de Agentic Web Search para verificação de fatos.
    
    1. Executa busca web em tempo real (5 resultados mais relevantes).
    2. Aplica prompt de sistema restrito com a Regra de Ouro do Filtro de Autoridade.
    3. Retorna objeto estruturado estritamente no schema JSON solicitado.
    4. Trata qualquer exceção (queda de rede, formato quebrado, timeout),
       garantindo o retorno seguro do status 'inconclusivo' sem interromper a aplicação.
    """
    try:
        texto_limpo = (afirmacao or "").strip()
        if not texto_limpo or len(texto_limpo) < 5:
            return {
                "status": "inconclusivo",
                "confianca": 0,
                "parecer": "Texto insuficiente para verificação institucional. Forneça uma alegação completa para checagem.",
                "fonte_recomendada": {
                    "nome": "Inexistente",
                    "url": None
                }
            }

        # Etapa 1: Busca Web dos 5 resultados mais relevantes
        excertos = buscar_web(texto_limpo, max_resultados=5)

        if not excertos:
            return RESULTADO_INCONCLUSIVO_PADRAO

        # Formatação dos excertos para injeção no prompt
        bloco_excertos = []
        for i, item in enumerate(excertos, start=1):
            bloco_excertos.append(
                f"[{i}] Título: {item['titulo']}\n"
                f"    Fonte/Portal: {item['portal']} ({item['url']})\n"
                f"    Excerto: {item['trecho']}"
            )
        excertos_texto = "\n\n".join(bloco_excertos)

        prompt_usuario = (
            f"Afirmação do usuário para auditoria:\n\"{texto_limpo}\"\n\n"
            f"Registros oficiais recuperados para auditoria:\n{excertos_texto}\n\n"
            "Retorne OBRIGATORIAMENTE um objeto JSON estrito com esta estrutura exata:\n"
            "{\n"
            '  "status": "fato" | "fake" | "alerta" | "inconclusivo",\n'
            '  "confianca": <inteiro de 0 a 100>,\n'
            '  "parecer": "<Texto explicativo curto e direto>",\n'
            '  "fonte_recomendada": {\n'
            '    "nome": "<Nome do portal ou Inexistente>",\n'
            '    "url": "<Link da matéria ou null>"\n'
            "  }\n"
            "}"
        )

        # Etapa 2 & 3: Chamada ao LLM com Prompt do Sistema
        resposta_llm = _executar_chamada_llm_api(PROMPT_SISTEMA, prompt_usuario)
        if resposta_llm:
            resultado_estruturado = _parse_resposta_json(resposta_llm)
            if resultado_estruturado:
                return resultado_estruturado

        # Fallback de autoridade local aplicando a exata mesma Regra de Ouro sobre os 5 excertos
        return _auditar_excertos_regra_de_ouro(texto_limpo, excertos)

    except Exception as exc:
        # Etapa 4: Tratamento de Exceções Robusto
        logger.error("Exceção capturada no pipeline de verificação agentic: %s", exc, exc_info=True)
        return RESULTADO_INCONCLUSIVO_PADRAO
