#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Laboratório 03 - DPoS sob a ótica eleitoral
Grupo G3 - Cartel / Conluio

Este arquivo executa um simulador de eleição DPoS e calcula métricas para a
patologia de cartel/conluio. Ele lê um CSV de cenários e gera um CSV de
resultados em formato longo: uma linha por combinação cenário x métrica x camada.

Uso principal:
    python simulador_dpos.py --cenarios cenarios.csv --saida resultados.csv

Também é possível gerar um arquivo de cenários padrão do G3:
    python simulador_dpos.py --gerar-cenarios cenarios.csv

Depois, executar:
    python simulador_dpos.py --cenarios cenarios.csv --saida resultados.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Configuração e contexto
# ---------------------------------------------------------------------------

@dataclass
class Config:
    n_holders: int = 1000
    distribuicao: str = "pareto"
    parametro_dist: float = 1.5
    n_candidatos: int = 80
    tamanho_comite: int = 21
    turnout: float = 0.5
    n_aprovacoes: int = 15
    n_blocos: int = 5000

    # Parâmetros de patologias / extensões
    frac_proxy: float = 0.0
    tam_cartel: int = 0
    orcamento_suborno: float = 0.0
    frac_exchange: float = 0.0
    frac_colludida: float = 0.0
    n_rodadas: int = 1
    vantagem_incumbencia: float = 0.0
    reinveste_recompensa: float = 0.0

    # Controle experimental
    metrica: str = "cartel_break_even;margem_limiar;peso_cartel;hhi"
    camada: str = "stake;eleito;produzido"
    n_runs: int = 30
    seed_base: int = 3100


@dataclass
class ContextoMetrica:
    cfg: Config
    camada: str
    shares: List[float]
    entidades: List[int]
    stakes: List[float]
    vota: List[bool]
    scores: Dict[int, float]
    eleitos: List[int]
    blocos: Dict[int, int]
    candidatos: List[int]
    cartel: Set[int]
    aprovacoes: Dict[int, Set[int]]
    peso_corte: float
    historico: List[dict]


# ---------------------------------------------------------------------------
# Leitura, validação e utilitários
# ---------------------------------------------------------------------------

CENARIO_COLUNAS = [
    "n_holders",
    "distribuicao",
    "parametro_dist",
    "n_candidatos",
    "tamanho_comite",
    "turnout",
    "n_aprovacoes",
    "n_blocos",
    "frac_proxy",
    "tam_cartel",
    "orcamento_suborno",
    "frac_exchange",
    "frac_colludida",
    "n_rodadas",
    "vantagem_incumbencia",
    "reinveste_recompensa",
    "metrica",
    "camada",
    "n_runs",
    "seed_base",
]

RESULTADO_COLUNAS = [
    "id_execucao",
    "id_cenario",
    *CENARIO_COLUNAS,
    "media",
    "ic95",
]


def _lista_csv(valor: str) -> List[str]:
    return [item.strip() for item in str(valor).split(";") if item.strip()]


def _float(row: dict, nome: str, padrao: float) -> float:
    valor = row.get(nome, "")
    if valor is None or str(valor).strip() == "":
        return padrao
    return float(str(valor).replace(",", "."))


def _int(row: dict, nome: str, padrao: int) -> int:
    valor = row.get(nome, "")
    if valor is None or str(valor).strip() == "":
        return padrao
    return int(float(str(valor).replace(",", ".")))


def config_from_row(row: dict) -> Config:
    cfg = Config()
    cfg.n_holders = _int(row, "n_holders", cfg.n_holders)
    cfg.distribuicao = str(row.get("distribuicao", cfg.distribuicao)).strip().lower()
    cfg.parametro_dist = _float(row, "parametro_dist", cfg.parametro_dist)
    cfg.n_candidatos = _int(row, "n_candidatos", cfg.n_candidatos)
    cfg.tamanho_comite = _int(row, "tamanho_comite", cfg.tamanho_comite)
    cfg.turnout = _float(row, "turnout", cfg.turnout)
    cfg.n_aprovacoes = _int(row, "n_aprovacoes", cfg.n_aprovacoes)
    cfg.n_blocos = _int(row, "n_blocos", cfg.n_blocos)
    cfg.frac_proxy = _float(row, "frac_proxy", cfg.frac_proxy)
    cfg.tam_cartel = _int(row, "tam_cartel", cfg.tam_cartel)
    cfg.orcamento_suborno = _float(row, "orcamento_suborno", cfg.orcamento_suborno)
    cfg.frac_exchange = _float(row, "frac_exchange", cfg.frac_exchange)
    cfg.frac_colludida = _float(row, "frac_colludida", cfg.frac_colludida)
    cfg.n_rodadas = _int(row, "n_rodadas", cfg.n_rodadas)
    cfg.vantagem_incumbencia = _float(row, "vantagem_incumbencia", cfg.vantagem_incumbencia)
    cfg.reinveste_recompensa = _float(row, "reinveste_recompensa", cfg.reinveste_recompensa)
    cfg.metrica = str(row.get("metrica", cfg.metrica)).strip()
    cfg.camada = str(row.get("camada", cfg.camada)).strip()
    cfg.n_runs = _int(row, "n_runs", cfg.n_runs)
    cfg.seed_base = _int(row, "seed_base", cfg.seed_base)
    validar_config(cfg)
    return cfg


def validar_config(cfg: Config) -> None:
    if cfg.n_holders <= 0:
        raise ValueError("n_holders deve ser positivo")
    if cfg.distribuicao not in {"pareto", "zipf", "lognormal", "uniforme"}:
        raise ValueError("distribuicao deve ser: pareto, zipf, lognormal ou uniforme")
    if cfg.parametro_dist <= 0:
        raise ValueError("parametro_dist deve ser positivo")
    if not 0 <= cfg.turnout <= 1:
        raise ValueError("turnout deve estar entre 0 e 1")
    if cfg.n_candidatos <= 0:
        raise ValueError("n_candidatos deve ser positivo")
    if cfg.n_candidatos > cfg.n_holders:
        raise ValueError("n_candidatos não pode ser maior que n_holders")
    if cfg.tamanho_comite <= 0:
        raise ValueError("tamanho_comite deve ser positivo")
    if cfg.tamanho_comite > cfg.n_candidatos:
        raise ValueError("tamanho_comite não pode ser maior que n_candidatos")
    if cfg.n_aprovacoes <= 0:
        raise ValueError("n_aprovacoes deve ser positivo")
    if cfg.n_blocos <= 0:
        raise ValueError("n_blocos deve ser positivo")
    if cfg.tam_cartel < 0:
        raise ValueError("tam_cartel deve ser maior ou igual a zero")
    if cfg.tam_cartel > cfg.n_candidatos:
        raise ValueError("tam_cartel não pode ser maior que n_candidatos")
    if cfg.n_runs < 1:
        raise ValueError("n_runs deve ser positivo")


def normalizar(valores: Sequence[float]) -> List[float]:
    total = sum(valores)
    if total <= 0:
        if not valores:
            return []
        return [1.0 / len(valores)] * len(valores)
    return [v / total for v in valores]


def media_ic95(valores: Sequence[float]) -> Tuple[float, float]:
    if not valores:
        return 0.0, 0.0
    media = statistics.fmean(valores)
    if len(valores) == 1:
        return media, 0.0
    desvio = statistics.stdev(valores)
    ic95 = 1.96 * desvio / math.sqrt(len(valores))
    return media, ic95


# ---------------------------------------------------------------------------
# Geração de stake
# ---------------------------------------------------------------------------


def gerar_stakes(cfg: Config, rng: random.Random) -> List[float]:
    """Gera stakes brutos segundo a distribuição configurada."""
    n = cfg.n_holders
    p = cfg.parametro_dist

    if cfg.distribuicao == "uniforme":
        valores = [rng.uniform(0.8, 1.2) for _ in range(n)]

    elif cfg.distribuicao == "lognormal":
        # parametro_dist é sigma; mu=0 para manter o foco na dispersão.
        valores = [rng.lognormvariate(0.0, p) for _ in range(n)]

    elif cfg.distribuicao == "pareto":
        # Em Pareto, expoente menor gera concentração maior.
        valores = [rng.paretovariate(p) for _ in range(n)]

    elif cfg.distribuicao == "zipf":
        # Aproximação determinística da cauda de Zipf com embaralhamento.
        # rank 1 recebe peso 1, rank 2 recebe 1/(2^p), etc.
        valores = [1.0 / ((i + 1) ** p) for i in range(n)]
        rng.shuffle(valores)

    else:
        raise ValueError(f"Distribuição inválida: {cfg.distribuicao}")

    return normalizar(valores)


# ---------------------------------------------------------------------------
# Motor da eleição DPoS
# ---------------------------------------------------------------------------


def escolher_aprovacoes(
    rng: random.Random,
    candidatos: Sequence[int],
    pesos_candidatos: Sequence[float],
    quantidade: int,
) -> Set[int]:
    """Escolhe candidatos por aprovação ponderada, sem repetição."""
    quantidade = min(quantidade, len(candidatos))
    escolhidos: Set[int] = set()

    # Tentativas repetidas com random.choices. Simples e suficiente para o tamanho do lab.
    tentativas_max = quantidade * 20 + 50
    tentativas = 0
    while len(escolhidos) < quantidade and tentativas < tentativas_max:
        escolhido = rng.choices(candidatos, weights=pesos_candidatos, k=1)[0]
        escolhidos.add(escolhido)
        tentativas += 1

    # Completa sem ponderação caso tenha havido muitas repetições.
    if len(escolhidos) < quantidade:
        restantes = [c for c in candidatos if c not in escolhidos]
        rng.shuffle(restantes)
        escolhidos.update(restantes[: quantidade - len(escolhidos)])

    return escolhidos


def simular_uma_eleicao(cfg: Config, seed: int) -> dict:
    rng = random.Random(seed)

    stakes = gerar_stakes(cfg, rng)
    holder_ids = list(range(cfg.n_holders))

    # Os candidatos são os holders mais ricos.
    candidatos = sorted(holder_ids, key=lambda i: stakes[i], reverse=True)[: cfg.n_candidatos]
    pesos_candidatos = [stakes[i] for i in candidatos]
    popularidade = normalizar(pesos_candidatos)

    # O cartel é formado pelos candidatos mais ricos. Eles coordenam votos entre si.
    cartel = set(candidatos[: cfg.tam_cartel])

    vota = [rng.random() < cfg.turnout for _ in holder_ids]

    # Cartel organizado sempre participa, pois a hipótese do G3 é coordenação.
    for membro in cartel:
        vota[membro] = True

    scores = {c: 0.0 for c in candidatos}
    aprovacoes: Dict[int, Set[int]] = {}

    for eleitor in holder_ids:
        if not vota[eleitor]:
            aprovacoes[eleitor] = set()
            continue

        aprovados = escolher_aprovacoes(
            rng=rng,
            candidatos=candidatos,
            pesos_candidatos=popularidade,
            quantidade=cfg.n_aprovacoes,
        )

        # Extensão G3: voto mútuo do cartel. Membros do cartel aprovam todos os membros
        # do cartel, simulando coordenação/coligação para fortalecer o bloco.
        if eleitor in cartel:
            aprovados.update(cartel)

        aprovacoes[eleitor] = aprovados
        peso_voto = stakes[eleitor]
        for candidato in aprovados:
            scores[candidato] += peso_voto

    # Se não houver votos, evita placar todo zerado usando popularidade como fallback.
    if sum(scores.values()) <= 0:
        for candidato in candidatos:
            scores[candidato] = stakes[candidato]

    # Apuração: top-k candidatos por score.
    ranking = sorted(candidatos, key=lambda c: scores[c], reverse=True)
    eleitos = ranking[: cfg.tamanho_comite]

    if len(ranking) > cfg.tamanho_comite:
        peso_corte = max(0.0, scores[ranking[cfg.tamanho_comite - 1]] - scores[ranking[cfg.tamanho_comite]])
    else:
        peso_corte = scores[ranking[-1]] if ranking else 0.0

    # Produção de blocos proporcional aos votos recebidos pelos eleitos.
    pesos_eleitos = [scores[e] for e in eleitos]
    if sum(pesos_eleitos) <= 0:
        pesos_eleitos = [1.0 for _ in eleitos]
    produtores = rng.choices(eleitos, weights=pesos_eleitos, k=cfg.n_blocos)
    blocos = {e: 0 for e in eleitos}
    for produtor in produtores:
        blocos[produtor] += 1

    # Camadas de poder.
    shares_stake = stakes[:]
    entidades_stake = holder_ids[:]

    scores_eleitos = [scores[e] for e in eleitos]
    shares_eleito = normalizar(scores_eleitos)
    entidades_eleito = eleitos[:]

    blocos_eleitos = [float(blocos[e]) for e in eleitos]
    shares_produzido = normalizar(blocos_eleitos)
    entidades_produzido = eleitos[:]

    return {
        "cfg": cfg,
        "stakes": stakes,
        "vota": vota,
        "scores": scores,
        "candidatos": candidatos,
        "cartel": cartel,
        "aprovacoes": aprovacoes,
        "eleitos": eleitos,
        "blocos": blocos,
        "peso_corte": peso_corte,
        "historico": [],
        "camadas": {
            "stake": (shares_stake, entidades_stake),
            "eleito": (shares_eleito, entidades_eleito),
            "produzido": (shares_produzido, entidades_produzido),
        },
    }


def criar_contexto(resultado: dict, camada: str) -> ContextoMetrica:
    if camada not in resultado["camadas"]:
        raise ValueError(f"Camada inválida: {camada}")
    shares, entidades = resultado["camadas"][camada]
    return ContextoMetrica(
        cfg=resultado["cfg"],
        camada=camada,
        shares=list(shares),
        entidades=list(entidades),
        stakes=list(resultado["stakes"]),
        vota=list(resultado["vota"]),
        scores=dict(resultado["scores"]),
        eleitos=list(resultado["eleitos"]),
        blocos=dict(resultado["blocos"]),
        candidatos=list(resultado["candidatos"]),
        cartel=set(resultado["cartel"]),
        aprovacoes={k: set(v) for k, v in resultado["aprovacoes"].items()},
        peso_corte=resultado["peso_corte"],
        historico=list(resultado["historico"]),
    )


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------


def metrica_gini(ctx: ContextoMetrica) -> float:
    xs = sorted([max(0.0, x) for x in ctx.shares])
    n = len(xs)
    total = sum(xs)
    if n == 0 or total == 0:
        return 0.0
    soma_ponderada = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * soma_ponderada) / (n * total) - (n + 1) / n


def metrica_hhi(ctx: ContextoMetrica) -> float:
    """Herfindahl-Hirschman Index: soma dos quadrados das fatias."""
    return sum(s * s for s in ctx.shares)


def metrica_nakamoto(ctx: ContextoMetrica, theta: float = 1.0 / 3.0) -> float:
    """
    Coeficiente de Nakamoto: menor número de entidades que ultrapassa o limiar theta.
    Para DPoS, theta=1/3 é útil para analisar blocos capazes de afetar liveness.
    """
    acumulado = 0.0
    for i, share in enumerate(sorted(ctx.shares, reverse=True), start=1):
        acumulado += share
        if acumulado > theta:
            return float(i)
    return float(len(ctx.shares))


def metrica_cartel_break_even(ctx: ContextoMetrica) -> float:
    """
    Métrica principal do G3.
    Interpretação: quantas entidades, começando pelas mais fortes, bastam para ultrapassar 1/3.
    Quanto menor, mais fácil um bloco/cartel atingir poder crítico.
    """
    return metrica_nakamoto(ctx, theta=1.0 / 3.0)


def peso_cartel_na_camada(ctx: ContextoMetrica) -> float:
    """Soma a fatia de poder dos membros do cartel presentes na camada atual."""
    return sum(share for entidade, share in zip(ctx.entidades, ctx.shares) if entidade in ctx.cartel)


def metrica_peso_cartel(ctx: ContextoMetrica) -> float:
    """
    Métrica adicional do G3.
    Mede diretamente a fatia de poder do cartel na camada analisada.
    """
    return peso_cartel_na_camada(ctx)


def metrica_margem_limiar(ctx: ContextoMetrica) -> float:
    """
    Métrica principal do G3.
    Margem até o limiar crítico de 1/3.
    Valor positivo: cartel ainda abaixo do limiar.
    Valor zero/próximo de zero: cartel no limite.
    Valor negativo: cartel ultrapassou 1/3 da camada analisada.
    """
    theta = 1.0 / 3.0
    return theta - peso_cartel_na_camada(ctx)


def metrica_jaccard_cartel(ctx: ContextoMetrica) -> float:
    """
    Métrica extra de detecção de conluio.
    Calcula a similaridade média de Jaccard entre os votos dos membros do cartel.
    Quanto mais próximo de 1, mais parecidas são as listas de aprovação do cartel.
    """
    membros = list(ctx.cartel)
    if len(membros) < 2:
        return 0.0

    valores = []
    for i in range(len(membros)):
        for j in range(i + 1, len(membros)):
            a = ctx.aprovacoes.get(membros[i], set())
            b = ctx.aprovacoes.get(membros[j], set())
            uniao = a | b
            if not uniao:
                valores.append(0.0)
            else:
                valores.append(len(a & b) / len(uniao))

    return statistics.fmean(valores) if valores else 0.0


METRICAS: Dict[str, Callable[[ContextoMetrica], float]] = {
    "gini": metrica_gini,
    "hhi": metrica_hhi,
    "nakamoto": metrica_nakamoto,
    "cartel_break_even": metrica_cartel_break_even,
    "margem_limiar": metrica_margem_limiar,
    "peso_cartel": metrica_peso_cartel,
    "jaccard_cartel": metrica_jaccard_cartel,
}


# ---------------------------------------------------------------------------
# Execução de cenários
# ---------------------------------------------------------------------------


def executar_cenario(cfg: Config, metricas: Sequence[str], camadas: Sequence[str]) -> Dict[Tuple[str, str], Tuple[float, float]]:
    valores: Dict[Tuple[str, str], List[float]] = {}
    for metrica in metricas:
        if metrica not in METRICAS:
            raise ValueError(f"Métrica desconhecida: {metrica}. Opções: {', '.join(sorted(METRICAS))}")
        for camada in camadas:
            valores[(metrica, camada)] = []

    for run in range(cfg.n_runs):
        seed = cfg.seed_base + run
        resultado = simular_uma_eleicao(cfg, seed)

        for metrica in metricas:
            func = METRICAS[metrica]
            for camada in camadas:
                ctx = criar_contexto(resultado, camada)
                valores[(metrica, camada)].append(float(func(ctx)))

    resumo: Dict[Tuple[str, str], Tuple[float, float]] = {}
    for chave, vals in valores.items():
        resumo[chave] = media_ic95(vals)
    return resumo


def ler_cenarios(caminho: str) -> List[dict]:
    with open(caminho, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def escrever_resultados(cenarios: List[dict], saida: str) -> None:
    id_execucao = datetime.now().strftime("%Y%m%d_%H%M%S")
    linhas = []

    for id_cenario, row in enumerate(cenarios, start=1):
        cfg = config_from_row(row)
        metricas = _lista_csv(cfg.metrica)
        camadas = _lista_csv(cfg.camada)
        resumo = executar_cenario(cfg, metricas, camadas)

        for metrica in metricas:
            for camada in camadas:
                media, ic95 = resumo[(metrica, camada)]
                linha = {
                    "id_execucao": id_execucao,
                    "id_cenario": id_cenario,
                    "n_holders": cfg.n_holders,
                    "distribuicao": cfg.distribuicao,
                    "parametro_dist": cfg.parametro_dist,
                    "n_candidatos": cfg.n_candidatos,
                    "tamanho_comite": cfg.tamanho_comite,
                    "turnout": cfg.turnout,
                    "n_aprovacoes": cfg.n_aprovacoes,
                    "n_blocos": cfg.n_blocos,
                    "frac_proxy": cfg.frac_proxy,
                    "tam_cartel": cfg.tam_cartel,
                    "orcamento_suborno": cfg.orcamento_suborno,
                    "frac_exchange": cfg.frac_exchange,
                    "frac_colludida": cfg.frac_colludida,
                    "n_rodadas": cfg.n_rodadas,
                    "vantagem_incumbencia": cfg.vantagem_incumbencia,
                    "reinveste_recompensa": cfg.reinveste_recompensa,
                    "metrica": metrica,
                    "camada": camada,
                    "n_runs": cfg.n_runs,
                    "seed_base": cfg.seed_base,
                    "media": f"{media:.8f}",
                    "ic95": f"{ic95:.8f}",
                }
                linhas.append(linha)

    with open(saida, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTADO_COLUNAS, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)


# ---------------------------------------------------------------------------
# Geração dos cenários do G3
# ---------------------------------------------------------------------------


def gerar_cenarios_g3(caminho: str) -> None:
    """
    Gera cenários do Grupo 3.

    Regra atendida:
    - varia dois parâmetros básicos com pelo menos três valores:
      n_holders = 200, 500, 1000
      tamanho_comite = 11, 21, 31
    - varia o parâmetro da patologia G3 com pelo menos três valores:
      tam_cartel = 0, 3, 6, 9
    - mede as métricas em três camadas:
      stake, eleito, produzido
    """
    n_holders_vals = [200, 500, 1000]
    tamanho_comite_vals = [11, 21, 31]
    tam_cartel_vals = [0, 3, 6, 9]

    linhas = []
    for n_holders in n_holders_vals:
        for tamanho_comite in tamanho_comite_vals:
            for tam_cartel in tam_cartel_vals:
                n_candidatos = max(80, tamanho_comite * 3)
                n_candidatos = min(n_candidatos, n_holders)
                linhas.append(
                    {
                        "n_holders": n_holders,
                        "distribuicao": "pareto",
                        "parametro_dist": 1.5,
                        "n_candidatos": n_candidatos,
                        "tamanho_comite": tamanho_comite,
                        "turnout": 0.5,
                        "n_aprovacoes": 15,
                        "n_blocos": 5000,
                        "frac_proxy": 0.0,
                        "tam_cartel": tam_cartel,
                        "orcamento_suborno": 0.0,
                        "frac_exchange": 0.0,
                        "frac_colludida": 0.0,
                        "n_rodadas": 1,
                        "vantagem_incumbencia": 0.0,
                        "reinveste_recompensa": 0.0,
                        "metrica": "cartel_break_even;margem_limiar;peso_cartel;hhi",
                        "camada": "stake;eleito;produzido",
                        "n_runs": 30,
                        "seed_base": 3100,
                    }
                )

    with open(caminho, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CENARIO_COLUNAS)
        writer.writeheader()
        writer.writerows(linhas)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador DPoS - G3 Cartel/Conluio")
    parser.add_argument("--cenarios", default="cenarios.csv", help="CSV de entrada com cenários")
    parser.add_argument("--saida", default="resultados.csv", help="CSV de saída com resultados")
    parser.add_argument("--gerar-cenarios", metavar="ARQUIVO", help="gera cenários padrão do G3 e encerra")
    args = parser.parse_args()

    if args.gerar_cenarios:
        gerar_cenarios_g3(args.gerar_cenarios)
        print(f"Cenários gerados em: {args.gerar_cenarios}")
        return

    cenarios = ler_cenarios(args.cenarios)
    escrever_resultados(cenarios, args.saida)
    print(f"Resultados gerados em: {args.saida}")


if __name__ == "__main__":
    main()
