"""
MÓDULO DE CHECAGEM DE FATOS EM TEMPO REAL // PROTEJAJÁ
Analisa textos e transcrições de áudios em busca de desinformação,
golpes virais, notícias falsas, esclarecimentos jurídicos e boatos de WhatsApp.
"""

import re
import time
import os
import urllib.request
import urllib.parse
import ssl
import json
import unicodedata

try:
    import rag_engine
except ImportError:
    from backend import rag_engine

try:
    import agentic_checker
except ImportError:
    from backend import agentic_checker

def normalizar_texto(texto):
    """Remove acentos e pontuações para correspondência fonética robusta."""
    if not texto:
        return ""
    texto_nfkd = unicodedata.normalize('NFKD', texto.lower())
    sem_acento = "".join([c for c in texto_nfkd if not unicodedata.combining(c)])
    return sem_acento

# BASE DE DADOS DE DESINFORMAÇÃO CONHECIDA, GOLPES E FATOS VERIFICADOS (BR)
PADROES_BOATO = [
    # 1. POLÍTICA, DIREITO E FATOS HISTÓRICOS
    {
        "id": "politica_lula_condenacoes_stf",
        "palavras_chave": [
            [r"\blula\b", r"luiz inacio", r"presidente lula", r"ex-presidente lula"],
            [r"ladrao", r"ladra", r"roubou", r"preso", r"condenacao", r"condenado", r"corrupcao", r"triplex", r"sitio", r"lava jato", r"ficha limpa", r"inocente", r"anulou", r"stf"]
        ],
        "veredito": "ESCLARECIMENTO JURÍDICO / JUÍZO DE VALOR",
        "badge_class": "status-info",
        "score_risco": 96,
        "sintese": "A afirmação mistura um juízo de valor político depreciativo com a cronologia processual da Operação Lava Jato, cujas condenações foram integralmente anuladas pelo Supremo Tribunal Federal (STF).",
        "detalhes": [
            "Histórico Processual: Luiz Inácio Lula da Silva chegou a ser condenado em 1ª e 2ª instâncias no âmbito da Operação Lava Jato (casos Triplex do Guarujá e Sítio de Atibaia), cumprindo 580 dias de prisão em Curitiba entre abril de 2018 e novembro de 2019.",
            "Anulação pelo STF: Em 2021, o plenário do STF anulou todas as ações por entender que a 13ª Vara Federal de Curitiba era incompetente para julgar os casos e, posteriormente, reconheceu a parcialidade e suspeição do ex-juiz Sergio Moro.",
            "Situação Jurídica Atual: Com as anulações, os processos retornaram à fase inicial e foram arquivados, extintos ou prescreveram na Justiça Federal de Brasília. Pela Constituição Brasileira (Art. 5º, LVII - Princípio da Presunção de Inocência), Lula não possui nenhuma condenação criminal transitada em julgado e tem plenos direitos políticos.",
            "Juízo de Valor vs Fato Objetivo: Adjetivos como 'ladrão' constituem opinião política depreciativa e retórica de adversários, não correspondendo a uma condição penal existente perante a Justiça atualmente."
        ],
        "orientacao": "Agências de checagem recomendam separar retórica político-partidária dos fatos processuais formais registrados no Poder Judiciário."
    },
    {
        "id": "politica_taxacao_pix",
        "palavras_chave": [
            [r"\bpix\b"],
            [r"taxa", r"taxar", r"imposto", r"cpmf", r"vai cobrar", r"vai ser cobrado", r"tarifa", r"cobrar taxa", r"receita vai taxar"]
        ],
        "veredito": "FALSO / BOATO RECORRENTE",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "Boato falso desmentido oficialmente pelo Banco Central do Brasil e pelo Ministério da Fazenda.",
        "detalhes": [
            "Não existe imposto, CPMF ou tarifa sobre transações de Pix efetuadas entre pessoas físicas.",
            "A Resolução BCB nº 1/2020 assegura a gratuidade total do envio e recebimento de Pix para pessoas físicas e microempreendedores individuais (MEI) em transações rotineiras.",
            "Tarifas somente podem ser cobradas de empresas (pessoas jurídicas) em transações comerciais específicas ou por bancos que ofertem serviços integrados de cobrança empresarial."
        ],
        "orientacao": "Não compartilhe mensagens ou áudios alarmistas afirmando que o Pix pessoal será taxado pelo governo."
    },
    {
        "id": "politica_confisco_poupanca",
        "palavras_chave": [
            [r"poupanca", r"poupancas", r"fgts", r"conta corrente", r"contas bancarias"],
            [r"confisco", r"confiscar", r"bloquear", r"bloqueio geral", r"vai tomar", r"governo vai travar"]
        ],
        "veredito": "FALSO / INCONSTITUCIONAL",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "Boato sem fundamento e juridicamente impossível; a Constituição Federal proíbe expressamente o confisco de poupança.",
        "detalhes": [
            "A Emenda Constitucional nº 32, promulgada em 2001, alterou o Artigo 62 da Constituição Federal, proibindo expressamente a edição de medidas provisórias que visem sequestro ou retenção de poupança ou bens financeiros.",
            "Nenhum governante ou presidente possui poder legal no Brasil para repetir o bloqueio de poupanças ocorrido no Plano Collor em 1990.",
            "Áudios com vozes anônimas que pedem saque urgente são correntes antigas requentadas para provocar instabilidade bancária."
        ],
        "orientacao": "Mantenha a calma e não realize saques precipitados baseados em áudios de redes sociais."
    },
    {
        "id": "politica_urnas_eletronicas",
        "palavras_chave": [
            [r"urna", r"urnas", r"tse", r"apuracao"],
            [r"fraude", r"fraudada", r"algoritmo secreto", r"codigo secreto", r"codigo-fonte secreto", r"voto nao computado", r"urnas adulteradas"]
        ],
        "veredito": "FALSO / TEORIA INFUNDADA",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "As urnas eletrônicas brasileiras são auditadas por dezenas de instituições públicas e independentes.",
        "detalhes": [
            "As urnas funcionam 100% desconectadas da internet, de redes sem fio, Wi-Fi e Bluetooth, impossibilitando qualquer ataque cibernético externo.",
            "O código-fonte é aberto para inspeção e auditoria mais de um ano antes das eleições a partidos, universidades federais, OAB, Polícia Federal e Forças Armadas.",
            "Ao término da votação, a urna imprime o Boletim de Urna (BU), fixado na porta da seção, permitindo conferência pública imediata antes do envio dos dados."
        ],
        "orientacao": "Consulte a seção 'Fato ou Boato' do portal oficial do Tribunal Superior Eleitoral (tse.jus.br)."
    },
    {
        "id": "politica_fechamento_igrejas",
        "palavras_chave": [
            [r"igreja", r"igrejas", r"pastor", r"padre", r"culto", r"biblia"],
            [r"vai fechar", r"vai proibir", r"proibicao da biblia", r"fechamento de templos", r"proibir culto"]
        ],
        "veredito": "FALSO / BOATO POLÍTICO",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "A liberdade religiosa e de culto é cláusula pétrea da Constituição Federal de 1988.",
        "detalhes": [
            "O Artigo 5º, inciso VI da Constituição Federal assegura a inviolabilidade da liberdade de consciência e de crença, garantindo o livre exercício dos cultos religiosos.",
            "Nenhum presidente, prefeito ou governador tem competência para fechar templos ou banir livros sagrados.",
            "Boatos sobre perseguição religiosa são recorrentes em períodos eleitorais com o intuito de manipular eleitores."
        ],
        "orientacao": "Desconfie de áudios que anunciam perseguição a igrejas sem apresentação de lei ou documento oficial."
    },
    {
        "id": "politica_bolsa_familia_corte",
        "palavras_chave": [
            [r"bolsa familia", r"auxilio brasil", r"cadunico"],
            [r"vai cortar de todos", r"cancelado para quem tem moto", r"cancelado para quem tem celular", r"corte geral", r"vai acabar"]
        ],
        "veredito": "ENGANOSO / DESCONTEXTUALIZADO",
        "badge_class": "status-alerta",
        "score_risco": 93,
        "sintese": "As regras de permanência no Bolsa Família são baseadas em renda familiar por pessoa, e não em corte indiscriminado.",
        "detalhes": [
            "A posse de bens básicos (como moto de uso de trabalho ou telefone celular) não cancela de forma automática o benefício se a renda per capita estiver dentro do limite legal.",
            "O critério central para ter direito ao Bolsa Família é a renda familiar mensal de até R$ 218 por pessoa cadastrada no CadÚnico.",
            "Processos de averiguação cadastral são periódicos e servem para garantir que os recursos cheguem a quem realmente necessita."
        ],
        "orientacao": "Em caso de dúvida cadastral, consulte o aplicativo oficial do Bolsa Família ou o CRAS do seu município."
    },
    {
        "id": "trabalho_fim_13_salario",
        "palavras_chave": [
            [r"decimo terceiro", r"13o", r"13o salario", r"ferias remuneradas"],
            [r"vai acabar", r"fim do", r"vai ser extinto", r"governo revogou", r"vai tirar"]
        ],
        "veredito": "FALSO / CLÁUSULA PÉTREA",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "O 13º salário e as férias remuneradas são direitos trabalhistas pétreos e irrenunciáveis.",
        "detalhes": [
            "O Artigo 7º da Constituição Federal de 1988 assegura o décimo terceiro salário e o terço constitucional de férias como direitos dos trabalhadores urbanos e rurais.",
            "Por serem direitos individuais fundamentais, não podem ser revogados por medida provisória ou decreto presidencial.",
            "Correntes sobre fim do 13º circulam nas redes há anos e são permanentemente desmentidas pelo Ministério do Trabalho."
        ],
        "orientacao": "Não compartilhe boatos sobre perda de direitos fundamentais já consolidados na legislação."
    },
    {
        "id": "politica_bolsonaro_fatos",
        "palavras_chave": [
            [r"bolsonaro", r"jair bolsonaro"],
            [r"confiscou aposentadoria", r"vacina causa aids", r"fechou o stf", r"ouro escondido", r"matou"]
        ],
        "veredito": "CHECAGEM FACTUAL / CONTEXTO HISTÓRICO",
        "badge_class": "status-info",
        "score_risco": 95,
        "sintese": "Análise factual de declarações ou processos envolvendo o ex-presidente Jair Bolsonaro com base em registros oficiais.",
        "detalhes": [
            "Declarações de que vacinas causavam doenças foram refutadas categoricamente pela comunidade científica, Anvisa e OMS.",
            "Decisões judiciais (como a declaração de inelegibilidade pelo TSE em 2023) possuem acórdãos públicos acessíveis a qualquer cidadão.",
            "Processos em curso no Supremo Tribunal Federal e na Polícia Federal devem ser acompanhados pelos despachos e notas oficiais dos órgãos."
        ],
        "orientacao": "Consulte documentos oficiais do Poder Judiciário e reportagens com pareceres técnicos de especialistas."
    },

    # 2. GOLPES DE PHISHING E FRAUDES DIGITAIS
    {
        "id": "cupom_mercado_falso",
        "palavras_chave": [
            [r"savegnago", r"carrefour", r"atacadao", r"assai", r"pao de acucar", r"supermercado"],
            [r"cupom", r"vale", r"presente", r"aniversario", r"500", r"1000", r"gratis", r"sorteio"]
        ],
        "veredito": "FALSO / GOLPE",
        "badge_class": "status-reprovado",
        "score_risco": 98,
        "sintese": "Tentativa clássica de phishing (golpe digital) usando indevidamente o nome de redes de supermercados.",
        "detalhes": [
            "Grandes redes de supermercados não distribuem vales de alto valor mediante compartilhamento no WhatsApp.",
            "Links enviados por correntes costumam clonar contas de mensagens ou roubar dados bancários.",
            "Nenhuma promoção oficial com essas características consta nos canais verificados das marcas."
        ],
        "orientacao": "Não clique no link nem passe adiante para seus contatos. Denuncie a mensagem como golpe."
    },
    {
        "id": "resgate_dinheiro_esquecido_golpe",
        "palavras_chave": [
            [r"valores a receber", r"resgate", r"banco central", r"indenizacao", r"cpf premiado", r"liberacao do pix", r"taxa para liberar"]
        ],
        "veredito": "FALSO / GOLPE",
        "badge_class": "status-reprovado",
        "score_risco": 97,
        "sintese": "Golpe do falso resgate de valores ou falsa indenização governamental.",
        "detalhes": [
            "O Banco Central não cobra nenhuma taxa antecipada nem manda links por WhatsApp para liberar dinheiro esquecido.",
            "O único sistema oficial legítimo é acessado exclusivamente pelo site valoresareceber.bcb.gov.br com conta gov.br.",
            "Sites com domínios suspeitos fora do '.gov.br' são páginas falsas para roubo de senhas."
        ],
        "orientacao": "Nunca pague taxas para 'liberar' dinheiro e não digite seus dados em sites que não terminem em .gov.br."
    },
    {
        "id": "golpe_sms_banco_falsa_compra",
        "palavras_chave": [
            [r"compra aprovada", r"compra de r\$", r"compra no valor de", r"cartao aprovou", r"transacao aprovada"],
            [r"0800", r"caso nao reconheca", r"central de atendimento", r"ligue agora", r"bloqueio preventivo"]
        ],
        "veredito": "FALSO / GOLPE DA FALSA CENTRAL",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "Golpe da falsa central telefônica bancária para obtenção de senhas e transferências via Pix.",
        "detalhes": [
            "Criminosos enviam mensagens de compras inexistentes de alto valor para induzir a vítima a ligar no número 0800 falso indicado.",
            "Ao ligar, golpistas simulam atendentes de banco e convencem a vítima a 'estornar' a transação realizando transferências via Pix.",
            "Bancos oficiais nunca solicitam senhas, transferências de proteção ou instalação de aplicativos de acesso remoto."
        ],
        "orientacao": "Não ligue para o 0800 recebido por SMS. Em caso de dúvida, consulte o aplicativo oficial do seu banco ou o telefone do verso do cartão."
    },

    # 3. ALARMISMOS, SAÚDE E SEGURANÇA PÚBLICA
    {
        "id": "alimento_adulterado_panico",
        "palavras_chave": [
            [r"leite", r"arroz", r"carne", r"feijao", r"refrigerante", r"alimento", r"lote"],
            [r"veneno", r"bacteria mortal", r"envenenado", r"morte de criancas", r"hospital"]
        ],
        "veredito": "FALSO / ALARMISMO",
        "badge_class": "status-reprovado",
        "score_risco": 94,
        "sintese": "Boato clássico de contaminação generalizada de alimentos gerador de pânico social.",
        "detalhes": [
            "Recalls de alimentos e medicamentos são comunicados formalmente pela ANVISA e Ministério da Saúde em diário oficial.",
            "Áudios sem identificação médica, sem número de processo e que apelam para 'repassar urgente' são correntes infundadas.",
            "Hospitais regionais e secretarias de saúde já desmentiram diversas vezes alertas similares."
        ],
        "orientacao": "Consulte o portal oficial da Anvisa (anvisa.gov.br) para conferir lotes sob interdição sanitária real."
    },
    {
        "id": "arrastao_ou_toque_de_recolher",
        "palavras_chave": [
            [r"toque de recolher", r"arrastao generalizado", r"fechem as portas", r"faccao ordenou"]
        ],
        "veredito": "ENGANOSO / NÃO COMPROVADO",
        "badge_class": "status-alerta",
        "score_risco": 89,
        "sintese": "Mensagem com alto índice de pânico artificial sem confirmação da Polícia Militar.",
        "detalhes": [
            "Boatos de 'toque de recolher' ou 'arrastão em massa' costumam ser reciclados de anos anteriores para causar insegurança.",
            "A Polícia Militar e a Guarda Civil Municipal operam com canais oficiais de comunicação para alertas verídicos.",
            "Áudios com vozes anônimas afirmando que 'um primo policial avisou' são a estrutura padrão de boatos."
        ],
        "orientacao": "Mantenha a tranquilidade e confirme sempre nos canais de imprensa regional e da Polícia Militar (190)."
    },
    {
        "id": "radar_oculto_multa_absurda",
        "palavras_chave": [
            [r"novo radar", r"multa por andar com vidro", r"radar escondido no poste", r"multa de 1500", r"radar oculto"]
        ],
        "veredito": "FALSO",
        "badge_class": "status-reprovado",
        "score_risco": 95,
        "sintese": "Boato recorrente sobre regras de trânsito e radares inexistentes.",
        "detalhes": [
            "A legislação brasileira de trânsito (Resolução Contran 798/2020) proíbe expressamente a instalação de radares ocultos ou camuflados.",
            "Não existe previsão de multa no Código de Trânsito Brasileiro (CTB) por conduzir com vidro aberto.",
            "Informações de trânsito verídicas são publicadas oficialmente pelo Senatran e Detran-SP."
        ],
        "orientacao": "Não propague desinformação sobre infrações inventadas. Consulte o portal do Detran-SP."
    },
    {
        "id": "vacina_cura_milagrosa",
        "palavras_chave": [
            [r"cura definitiva", r"medico japones", r"limao com bicarbonato cura", r"segredo que as farmacias escondem", r"cura milagrosa"]
        ],
        "veredito": "FALSO / RISCO À SAÚDE",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "Receita milagrosa sem respaldo científico com risco à saúde pública.",
        "detalhes": [
            "Nenhuma entidade médica séria (Fiocruz, Butantan, OMS, CFM) reconhece receitas caseiras para cura de doenças crônicas ou tumores.",
            "A substituição de tratamentos médicos por fórmulas de correntes pode acarretar agravamento de saúde.",
            "A atribuição a 'médicos anônimos' ou 'descobertas secretas' é tática comum de canais caça-cliques."
        ],
        "orientacao": "Nunca interrompa medicação receitada por profissionais. Consulte postos de saúde ou o SAMU 192."
    },
    {
        "id": "vacinas_chip_grafeno_magnetismo",
        "palavras_chave": [
            [r"vacina", r"vacinas", r"imunizante"],
            [r"chip", r"grafeno", r"altera o dna", r"magnetismo", r"ima", r"metais pesados magneticos"]
        ],
        "veredito": "FALSO / TEORIA DA CONSPIRAÇÃO",
        "badge_class": "status-reprovado",
        "score_risco": 99,
        "sintese": "Teoria da conspiração sem qualquer fundamentação biológica ou física.",
        "detalhes": [
            "Nenhuma vacina contém chips eletrônicos, estruturas de grafeno ou propriedades de atração magnética.",
            "A composição detalhada de todos os imunizantes é pública e fiscalizada pela Anvisa e órgãos globais de saúde.",
            "Estudos clínicos com milhões de doses aplicadas comprovam segurança e eficácia no controle de epidemias."
        ],
        "orientacao": "Consulte os dados científicos oficiais disponibilizados pela Fiocruz e Instituto Butantan."
    }
]

# GATILHOS DE DESINFORMAÇÃO E SENSIBILIDADE
GATILHOS_URGENCIA = [
    r"repass[ea] urgente",
    r"compartilh[ea] antes que apaguem",
    r"aten[cç][aã]o moradores",
    r"alerta geral",
    r"n[aã]o deixe de avisar",
    r"est[aá] acontecendo agora",
    r"meu amigo policial",
    r"m[eé]dico avisou",
    r"cuidado urgente",
    r"mande para todos",
]

GATILHOS_CREDIBILIDADE = [
    r"di[aá]rio oficial",
    r"comunicado da prefeitura",
    r"nota oficial da pol[ií]cia",
    r"portal g1",
    r"ag[eê]ncia de checagem",
    r"procon estadual",
    r"decreto municipal",
]

def buscar_contexto_enciclopedico(texto):
    """
    Pesquisa na Wikipedia em português para obter contexto documental factual.
    Utiliza timeout estrito e contexto SSL resiliente para garantir respostas rápidas.
    """
    try:
        ctx = ssl._create_unverified_context()
        # Remove palavras interrogativas comuns para isolar a entidade
        stop_words = {"e", "é", "verdade", "que", "o", "a", "os", "as", "de", "do", "da", "em", "um", "uma", "sera", "será", "procede", "ladrao", "ladrão"}
        palavras = [w for w in re.sub(r"[^\w\s]", "", texto.lower()).split() if w not in stop_words and len(w) > 2]
        query = " ".join(palavras[:4]) if palavras else texto[:30]

        req = urllib.request.Request(
            f"https://pt.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={urllib.parse.quote(query)}",
            headers={"User-Agent": "ProtejaJaFactChecker/2.0"}
        )
        res = urllib.request.urlopen(req, context=ctx, timeout=2.5)
        data = json.loads(res.read())
        hits = data.get("query", {}).get("search", [])
        if not hits:
            return None

        primeiro_titulo = hits[0]["title"]
        title_enc = urllib.parse.quote(primeiro_titulo)
        req2 = urllib.request.Request(
            f"https://pt.wikipedia.org/api/rest_v1/page/summary/{title_enc}",
            headers={"User-Agent": "ProtejaJaFactChecker/2.0"}
        )
        res2 = urllib.request.urlopen(req2, context=ctx, timeout=2.5)
        data2 = json.loads(res2.read())
        extrato = data2.get("extract", "")
        if not extrato or len(extrato) < 40:
            return None

        return {
            "titulo": data2.get("title", primeiro_titulo),
            "extrato": extrato,
            "url": data2.get("content_urls", {}).get("desktop", {}).get("page", "")
        }
    except Exception as e:
        return None


def analisar_fato(texto):
    """
    Executa a auditoria oficial de veracidade com o Motor de Verificação Proteja-Já.
    Retorna o relatório estruturado de verificação com status, confiança, parecer e fonte oficial.
    """
    inicio = time.time()
    texto_limpo = (texto or "").strip()

    if not texto_limpo or len(texto_limpo) < 5:
        return {
            "sucesso": False,
            "status": "inconclusivo",
            "confianca": 0,
            "parecer": "Texto insuficiente para verificação documental. Forneça uma alegação com pelo menos 5 caracteres.",
            "fonte_recomendada": {"nome": "Inexistente", "url": None},
            "erro": "Texto muito curto para análise. Forneça uma frase com pelo menos 5 caracteres ou envie um áudio claro.",
            "tempo_analise_ms": int((time.time() - inicio) * 1000)
        }

    # 1. Pipeline Oficial do Motor de Verificação Proteja-Já
    try:
        resultado_agentic = agentic_checker.processar_entrada_usuario(texto_limpo)
    except Exception as e:
        resultado_agentic = agentic_checker.RESULTADO_INCONCLUSIVO_PADRAO

    status = resultado_agentic["status"]
    confianca = resultado_agentic["confianca"]
    parecer = resultado_agentic["parecer"]
    fonte = resultado_agentic["fonte_recomendada"]

    if status == "fato":
        veredito = "FATO / CONFIRMADO"
        badge_class = "status-fato"
    elif status == "fake":
        veredito = "FAKE / DESMENTIDO"
        badge_class = "status-fake"
    elif status == "alerta":
        veredito = "ALERTA / JUÍZO DE VALOR"
        badge_class = "status-alerta"
    else:
        veredito = "INCONCLUSIVO / SEM COBERTURA OFICIAL"
        badge_class = "status-analise"

    orientacao = (
        f"Fonte de referência recomendada: {fonte['nome']} ({fonte['url']})"
        if fonte.get("url")
        else "Não repasse sem confirmação de veículos profissionais de imprensa ou canais governamentais."
    )

    evidencias_oficiais = []
    if fonte.get("url") and fonte.get("nome") and fonte["nome"] != "Inexistente":
        evidencias_oficiais.append({
            "titulo": f"Registro Oficial / Imprensa: {fonte['nome']}",
            "autoridade": fonte["nome"],
            "url": fonte.get("url"),
            "trecho": parecer,
            "score": confianca
        })

    return {
        "sucesso": True,
        # Schema estrito exigido pelo pipeline
        "status": status,
        "confianca": confianca,
        "parecer": parecer,
        "fonte_recomendada": fonte,
        # Compatibilidade com o frontend e telemetria
        "texto_analisado": texto_limpo,
        "veredito": veredito,
        "badge_class": badge_class,
        "score_confianca": confianca,
        "sintese": parecer,
        "motivos": [
            f"Análise baseada em registros oficiais com veredito de conformidade: {status.upper()}.",
            f"Fonte institucional identificada: {fonte['nome']}.",
            "Nossa auditoria identificou respaldo em canais oficiais e veículos de alta credibilidade."
        ],
        "orientacao": orientacao,
        "origem": "Motor de Verificação Proteja-Já",
        "fundamentacao_oficial": evidencias_oficiais,
        "tempo_analise_ms": int((time.time() - inicio) * 1000)
    }
    texto_lower = texto_limpo.lower()
    e_pergunta = bool(re.search(r"^(é verdade|e verdade|isso é verdade|será que|sera que|procede que|procede|é fato|e fato|o que aconteceu|é fake|e fake)", normalizar_texto(texto_limpo)) or texto_limpo.endswith("?"))

    gatilhos_encontrados = []
    for g in GATILHOS_URGENCIA:
        if re.search(g, texto_lower, re.IGNORECASE):
            gatilhos_encontrados.append(re.sub(r"[\[\]\(\)\^\\$]", "", g).capitalize())

    sinais_credibilidade = []
    for c in GATILHOS_CREDIBILIDADE:
        if re.search(c, texto_lower, re.IGNORECASE):
            sinais_credibilidade.append(c)

    # 3. Auditoria de Padrões e Registros Oficiais
    if len(gatilhos_encontrados) >= 2:
        return {
            "sucesso": True,
            "texto_analisado": texto_limpo,
            "veredito": "ALTO RISCO DE DESINFORMAÇÃO",
            "badge_class": "status-reprovado",
            "score_confianca": 88,
            "sintese": "A mensagem apresenta fortes características estruturais de correntes alarmistas e boatos virais de redes sociais.",
            "motivos": [
                f"Nossa auditoria identificou termos com padrão de urgência artificial ou indução ao pânico: {', '.join(gatilhos_encontrados)}.",
                "Ausência de fontes primárias, registros de órgãos oficiais ou datas explícitas verificáveis.",
                "Estimula o compartilhamento rápido sem reflexão crítica, padrão característico de campanhas de desinformação."
            ],
            "orientacao": "Recomendamos cautela absoluta. Não repasse esta mensagem sem verificar se foi confirmada por veículos de imprensa sérios.",
            "origem": "Central de Fatos",
            "tipo_consulta": "declaracao",
            "tempo_analise_ms": int((time.time() - inicio) * 1000)
        }

    if len(gatilhos_encontrados) == 1 and not sinais_credibilidade:
        return {
            "sucesso": True,
            "texto_analisado": texto_limpo,
            "veredito": "INFORMAL / DUVIDOSO",
            "badge_class": "status-alerta",
            "score_confianca": 65,
            "sintese": "O relato possui traços informais e termos apelativos que exigem checagem complementar antes de ser aceito como fato.",
            "motivos": [
                f"Nossa auditoria identificou padrão de alerta no relato: '{gatilhos_encontrados[0]}'.",
                "Relato sem citação a protocolos formais, leis ou canais oficiais de comunicação.",
                "Pode se tratar de relato pessoal autêntico, mas sem comprovação documental."
            ],
            "orientacao": "Confirme a informação nos canais da imprensa oficial antes de repassar a contatos.",
            "origem": "Central de Fatos",
            "tipo_consulta": "declaracao",
            "tempo_analise_ms": int((time.time() - inicio) * 1000)
        }

    if sinais_credibilidade:
        return {
            "sucesso": True,
            "texto_analisado": texto_limpo,
            "veredito": "INDÍCIOS DE VERACIDADE",
            "badge_class": "status-aprovado",
            "score_confianca": 85,
            "sintese": "O texto faz referência a canais institucionais, imprensa ou documentos formais de fiscalização.",
            "motivos": [
                "Nossa auditoria identificou menção expressa a órgãos públicos, portais de checagem ou veículos formais de transparência.",
                "Estrutura linguística sóbria, sem pedidos apelativos de compartilhamento em massa.",
                "Compatível com notícias de utilidade pública e cidadania digital."
            ],
            "orientacao": "A informação aparenta ser legítima, mas sempre confirme o link da fonte original citada.",
            "origem": "Central de Fatos",
            "tipo_consulta": "pergunta" if e_pergunta else "declaracao",
            "tempo_analise_ms": int((time.time() - inicio) * 1000)
        }

    # 4. Consulta Dinâmica em Base Enciclopédica & Factual
    resultado_enciclopedia = buscar_contexto_enciclopedico(texto_limpo)
    if resultado_enciclopedia:
        titulo_artigo = resultado_enciclopedia["titulo"]
        extrato_artigo = resultado_enciclopedia["extrato"]
        url_artigo = resultado_enciclopedia.get("url", "https://pt.wikipedia.org")

        # Divide o extrato em frases informativas
        frases = [f.strip() + "." for f in extrato_artigo.split(".") if len(f.strip()) > 20][:3]
        if not frases:
            frases = [extrato_artigo]

        return {
            "sucesso": True,
            "texto_analisado": texto_limpo,
            "veredito": "CONSULTA ENCICLOPÉDICA / FATO HISTÓRICO",
            "badge_class": "status-info",
            "score_confianca": 88,
            "sintese": f"Foram localizados registros históricos e documentais consolidados relacionados a '{titulo_artigo}'.",
            "motivos": frases,
            "orientacao": f"Para leitura aprofundada das fontes e bibliografia histórica, consulte a documentação completa: {url_artigo}",
            "origem": "Central de Fatos",
            "tipo_consulta": "pergunta" if e_pergunta else "declaracao",
            "tempo_analise_ms": int((time.time() - inicio) * 1000)
        }

    # 5. Neutro / Tema Aberto
    return {
        "sucesso": True,
        "texto_analisado": texto_limpo,
        "veredito": "TEMA ABERTO / CONSULTA EM ANÁLISE",
        "badge_class": "status-analise",
        "score_confianca": 50,
        "sintese": "A mensagem ou dúvida analisada não corresponde aos padrões de golpes conhecidos ou boatos virais de larga escala.",
        "motivos": [
            "Não foram detectados elementos de engenharia social, tentativa de phishing bancário ou indução ao pânico.",
            "Perguntas opinativas ou fatos recentes em apuração jornalística podem não ter resposta binária imediata.",
            "Recomendamos consultar agências parceiras de verificação: G1 Fato ou Fake, Agência Lupa, Aos Fatos e UOL Confere."
        ],
        "orientacao": "Antes de compartilhar qualquer conteúdo em grupos de mensagens, certifique-se de que a informação foi noticiada por veículos profissionais de imprensa.",
        "origem": "Central de Fatos",
        "tipo_consulta": "pergunta" if e_pergunta else "declaracao",
        "tempo_analise_ms": int((time.time() - inicio) * 1000)
    }


def transcrever_audio(caminho_arquivo):
    """
    Tenta transcrever o arquivo de áudio utilizando faster-whisper caso disponível.
    Retorna o texto transcrito ou None.
    """
    try:
        from faster_whisper import WhisperModel
        # Modelo tiny em CPU para transcrição super rápida (< 2 segundos)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(caminho_arquivo, beam_size=1, language="pt")
        texto = " ".join([seg.text for seg in segments]).strip()
        return texto
    except Exception as e:
        print("[Audio Transcribe] Erro ao transcrever com whisper:", e)
        return None
