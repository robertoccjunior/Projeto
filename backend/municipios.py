import json
import os
import unicodedata

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "municipios.json")


def _normalizar_texto(texto: str) -> str:
    """Remove acentos, converte para minúsculas e remove espaços extras."""
    if not texto:
        return ""
    nfd = unicodedata.normalize("NFD", texto.strip())
    sem_acentos = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return " ".join(sem_acentos.lower().split())


def _carregar_base():
    if not os.path.exists(DATA_PATH):
        return [], {}, []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        lista = json.load(f)
    indice = []
    mapa_canonico = {}
    for item in lista:
        norm = _normalizar_texto(item)
        indice.append((norm, item))
        mapa_canonico[norm] = item
    return lista, mapa_canonico, indice


_MUNICIPIOS, _MAPA_CANONICO, _INDICE = _carregar_base()


def total_municipios() -> int:
    return len(_MUNICIPIOS)


def normalizar_municipio(cidade: str) -> str | None:
    """
    Valida se a string informada corresponde a um município brasileiro oficial
    no formato 'Cidade - UF' (insensível a acentos e maiúsculas/minúsculas).
    Retorna o nome canônico 'Cidade - UF' ou None se inválido.
    """
    norm = _normalizar_texto(cidade)
    if not norm:
        return None
    return _MAPA_CANONICO.get(norm)


def buscar_municipios(termo: str, limite: int = 10) -> list[str]:
    """
    Busca municípios brasileiros por prefixo (prioritário) ou substring,
    normalizando acentos e caixa, retornando no máximo `limite` itens.
    """
    q = _normalizar_texto(termo)
    if not q:
        return []
    limite = max(1, min(int(limite), 25))

    prefixos = []
    contem = []
    for norm, original in _INDICE:
        if norm.startswith(q):
            prefixos.append(original)
            if len(prefixos) >= limite:
                return prefixos
        elif q in norm:
            contem.append(original)

    return (prefixos + contem)[:limite]
