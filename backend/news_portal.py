import html
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

_CACHE = {"ts": 0.0, "itens": []}
_CACHE_TTL = 900  # 15 minutos

FEEDS_OFICIAIS = [
    {
        "fonte": "Agência Brasil (EBC)",
        "url": "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",
        "categoria_padrao": "impostos",
    },
    {
        "fonte": "Agência Brasil (Justiça)",
        "url": "https://agenciabrasil.ebc.com.br/rss/justica/feed.xml",
        "categoria_padrao": "golpes",
    },
    {
        "fonte": "G1 Economia",
        "url": "https://g1.globo.com/rss/g1/economia/",
        "categoria_padrao": "impostos",
    },
]

ALERTAS_RESERVA = [
    {
        "titulo": "Golpe do falso cupom e Pix premiado: como identificar links fraudulentos",
        "resumo": "Criminosos usam nomes de grandes redes e órgãos públicos para pedir taxas via Pix. Nunca pague para liberar benefícios ou descontos.",
        "link": "https://www.bcb.gov.br/meubc/faqs/p/golpes-envolvendo-o-pix",
        "fonte": "Banco Central do Brasil",
        "categoria": "golpes",
        "publicado_em": "Alerta Permanente",
    },
    {
        "titulo": "Não existe cobrança de taxa ou imposto sobre transferências via Pix",
        "resumo": "A Receita Federal reforça que boatos sobre taxação do Pix para pessoas físicas são falsos e costumam acompanhar golpes de phishing.",
        "link": "https://www.gov.br/receitafederal/pt-br",
        "fonte": "Receita Federal",
        "categoria": "impostos",
        "publicado_em": "Comunicado Oficial",
    },
    {
        "titulo": "Direitos do consumidor: cobrança indevida garante devolução em dobro",
        "resumo": "Conforme o art. 42 do Código de Defesa do Consumidor, valores cobrados indevidamente devem ser restituídos em dobro, salvo engano justificável.",
        "link": "https://www.gov.br/mj/pt-br/assuntos/seus-direitos/consumidor",
        "fonte": "Senacon / Consumidor.gov.br",
        "categoria": "consumidor",
        "publicado_em": "Orientação Oficial",
    },
    {
        "titulo": "Transparência nos gastos públicos: acompanhe contratos e repasses",
        "resumo": "Cidadãos podem fiscalizar empenhos, licitações e despesas com impostos federais diretamente nos portais oficiais de transparência.",
        "link": "https://portaldatransparencia.gov.br/",
        "fonte": "Portal da Transparência",
        "categoria": "impostos",
        "publicado_em": "Utilidade Pública",
    },
]


def _limpar_html(texto: str) -> str:
    sem_tags = re.sub(r"<[^>]+>", " ", texto or "")
    limpo = html.unescape(" ".join(sem_tags.split()))
    return limpo[:220] + ("..." if len(limpo) > 220 else "")


def _classificar_categoria(titulo: str, resumo: str, padrao: str) -> str:
    txt = f"{titulo} {resumo}".lower()
    if any(k in txt for k in ("golpe", "fraude", "estelionato", "falso", "fake", "roubo", "furto", "crime", "pix", "phishing")):
        return "golpes"
    if any(k in txt for k in ("imposto", "tributo", "receita federal", "gasto público", "orçamento", "taxa", "inflação", "icms", "irpf", "dinheiro público")):
        return "impostos"
    if any(k in txt for k in ("consumidor", "procon", "anvisa", "produto", "preço", "serviço", "segurança")):
        return "consumidor"
    return padrao


def _baixar_feed(feed_cfg: dict) -> list[dict]:
    req = urllib.request.Request(
        feed_cfg["url"],
        headers={"User-Agent": "Mozilla/5.0 (compatible; ProtejaJaPortal/1.0)"},
    )
    itens = []
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            xml_bytes = resp.read(300000)
        root = ET.fromstring(xml_bytes)
        for item in root.findall(".//item")[:6]:
            titulo = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = _limpar_html(item.findtext("description") or "")
            pub = (item.findtext("pubDate") or "").strip()[:16] or "Recente"
            if titulo and link.startswith("http"):
                cat = _classificar_categoria(titulo, desc, feed_cfg["categoria_padrao"])
                itens.append({
                    "titulo": html.unescape(titulo),
                    "resumo": desc or "Confira a matéria completa na fonte oficial.",
                    "link": link,
                    "fonte": feed_cfg["fonte"],
                    "categoria": cat,
                    "publicado_em": pub,
                })
    except Exception:
        return []
    return itens


def obter_noticias(categoria: str = "todas", limite: int = 12) -> list[dict]:
    agora = time.time()
    if not _CACHE["itens"] or (agora - _CACHE["ts"]) > _CACHE_TTL:
        coletados = []
        for cfg in FEEDS_OFICIAIS:
            coletados.extend(_baixar_feed(cfg))
        # Mescla notícias ao vivo com alertas oficiais de referência
        vistos = set()
        unicos = []
        for it in coletados + ALERTAS_RESERVA:
            chave = it["titulo"].lower()
            if chave not in vistos:
                vistos.add(chave)
                unicos.append(it)
        _CACHE["itens"] = unicos
        _CACHE["ts"] = agora

    itens = _CACHE["itens"]
    cat = (categoria or "todas").strip().lower()
    if cat and cat != "todas":
        filtrados = [i for i in itens if i["categoria"] == cat]
        return filtrados[:limite]
    return itens[:limite]
