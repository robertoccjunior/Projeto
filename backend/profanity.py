import re
import unicodedata

PALAVRAS_BLOQUEADAS = {
    "arrombado",
    "arrombada",
    "babaca",
    "biscate",
    "bixa",
    "boceta",
    "bosta",
    "buceta",
    "cabaco",
    "cacete",
    "caralho",
    "corno",
    "cornuda",
    "cretino",
    "cretina",
    "cu",
    "desgracado",
    "desgracada",
    "fdp",
    "foda",
    "fode",
    "foder",
    "fodido",
    "fodida",
    "fudido",
    "fudida",
    "imbecil",
    "merda",
    "otario",
    "otaria",
    "pentelho",
    "piroca",
    "porra",
    "piranha",
    "punheta",
    "puta",
    "puto",
    "rapariga",
    "retardado",
    "retardada",
    "sacana",
    "vagabunda",
    "vagabundo",
    "vadia",
    "vadio",
    "viado",
    "xaninha",
    "xota",
    "filho da puta",
    "filha da puta",
    "vai tomar no cu",
    "vai se foder",
    "tomar no cu",
    "pau no cu",
}

_TROCA_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i", "2": "z"}
)


def _sem_acentos(texto):
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _normalizar(texto):
    return _sem_acentos(texto).lower().translate(_TROCA_LEET)


def _padrao_deteccao():
    termos = sorted(PALAVRAS_BLOQUEADAS, key=len, reverse=True)
    return re.compile(r"\b(?:%s)\b" % "|".join(re.escape(t) for t in termos))


_PADRAO_DETECCAO = _padrao_deteccao()
_PADRAO_EXIBICAO = re.compile(
    r"\b(?:%s)\b"
    % "|".join(
        re.escape(t)
        for t in sorted(
            set(PALAVRAS_BLOQUEADAS) | {_sem_acentos(t) for t in PALAVRAS_BLOQUEADAS},
            key=len,
            reverse=True,
        )
    ),
    re.IGNORECASE,
)


def contem_ofensa(texto):
    if not texto:
        return False
    return bool(_PADRAO_DETECCAO.search(_normalizar(str(texto))))


def sanitizar(texto):
    if not texto:
        return str(texto or "")

    original = str(texto)
    if not contem_ofensa(original):
        return original

    def substituir(match):
        return "*" * min(len(match.group(0)), 6)

    return _PADRAO_EXIBICAO.sub(substituir, original)