# Simulador DPoS - G3 Cartel e Conluio

Este repositório contém o simulador do Grupo 3 para o laboratório de DPoS.  
O objetivo é analisar a patologia de **cartel/conluio**, verificando como um grupo coordenado de candidatos ou delegados pode concentrar poder em uma eleição baseada em Delegated Proof of Stake.

No DPoS, os detentores de tokens votam em candidatos a produtores de bloco. O peso do voto é proporcional ao stake de cada eleitor. Os candidatos mais votados formam um comitê responsável pela produção dos blocos. Esse modelo melhora o desempenho da rede, mas pode gerar concentração política quando poucos participantes conseguem controlar a eleição.

## Grupo e patologia

Grupo: **G3**

Patologia analisada:

```text
Cartel / Conluio
```

Parâmetro principal:

```text
tam_cartel
```

Esse parâmetro representa o número de membros que fazem parte do cartel.

## Objetivo do experimento

O experimento busca responder:

- O aumento do cartel concentra mais poder?
- O cartel afeta mais a camada de stake, a camada dos eleitos ou a produção de blocos?
- Comitês maiores reduzem o risco de cartelização?
- A concentração de riqueza facilita a atuação do cartel?

Para isso, o simulador executa várias eleições DPoS com diferentes combinações de parâmetros e calcula métricas de concentração e risco.

## Camadas analisadas

As métricas são calculadas em três camadas:

| Camada      | Significado                                      |
| ----------- | ------------------------------------------------ |
| `stake`     | Distribuição inicial de riqueza entre os holders |
| `eleito`    | Distribuição de poder entre os delegados eleitos |
| `produzido` | Distribuição efetiva da produção de blocos       |

A comparação entre essas camadas é importante porque a eleição pode amplificar a concentração existente no stake.

## Parâmetros variados

O experimento varia os seguintes parâmetros:

| Parâmetro        | Valores        | Significado                                  |
| ---------------- | -------------- | -------------------------------------------- |
| `n_holders`      | 200, 500, 1000 | Quantidade de detentores de tokens           |
| `tamanho_comite` | 11, 21, 31     | Número de delegados eleitos                  |
| `parametro_dist` | 1.2, 1.5, 2.0  | Nível de concentração da distribuição Pareto |
| `tam_cartel`     | 0, 3, 6, 9     | Número de membros do cartel                  |

Na distribuição Pareto, valores menores de `parametro_dist` indicam maior concentração de riqueza.

## Parâmetros mantidos zerados

Alguns parâmetros aparecem no CSV, mas ficam zerados porque pertencem a outras patologias:

| Parâmetro              | Patologia relacionada       |
| ---------------------- | --------------------------- |
| `orcamento_suborno`    | Compra de voto              |
| `frac_exchange`        | Voto custodiado             |
| `frac_colludida`       | Censura                     |
| `vantagem_incumbencia` | Entrincheiramento           |
| `reinveste_recompensa` | Concentração de recompensas |

Eles foram mantidos em zero para isolar o efeito do cartel. Assim, os resultados não misturam diferentes causas de concentração.

## Métricas implementadas

### cartel_break_even

Mede quantas entidades são necessárias para ultrapassar um limiar crítico de poder.

Quanto menor o valor, maior o risco, pois poucas entidades já conseguem concentrar poder relevante.

### margem_limiar

Mede a distância entre o peso do cartel e o limiar crítico de 1/3.

Interpretação:

| Valor           | Significado                    |
| --------------- | ------------------------------ |
| Positivo        | O cartel está abaixo do limiar |
| Próximo de zero | O cartel está perto do limiar  |
| Negativo        | O cartel ultrapassou o limiar  |

### peso_cartel

Mede a fração de poder concentrada pelos membros do cartel.

Quanto maior o valor, maior a influência direta do cartel.

### hhi

Mede concentração de poder.

Valores maiores indicam maior concentração.

### jaccard_cartel

Mede a similaridade entre padrões de votação associados ao cartel.

Valores maiores podem indicar comportamento mais coordenado.

## Estrutura do repositório

```text
dpos-g3-cartel/
├── simulador_dpos.py
├── cenarios.csv
├── resultados.csv
├── README.md
└── estrutura_relatorio.md
```

## Arquivos

### simulador_dpos.py

Arquivo principal do projeto. Ele lê os cenários, executa as simulações, calcula as métricas e gera o arquivo de resultados.

### cenarios.csv

Arquivo de entrada do simulador. Cada linha representa um cenário experimental.

### resultados.csv

Arquivo de saída do simulador. Cada linha representa o resultado de uma combinação entre cenário, métrica e camada.

As colunas principais são:

| Coluna            | Significado                        |
| ----------------- | ---------------------------------- |
| `id_cenario`      | Identificador do cenário           |
| `metrica`         | Métrica calculada                  |
| `camada`          | Camada analisada                   |
| `media`           | Média das simulações               |
| `ic95`            | Intervalo de confiança de 95%      |
| `valor_legivel`   | Valor em formato mais fácil de ler |
| `cenario_legivel` | Descrição textual do cenário       |
| `interpretacao`   | Interpretação curta do resultado   |

## Requisitos

O projeto utiliza apenas Python e bibliotecas padrão.

Versão recomendada:

```text
Python 3.10 ou superior
```

Verifique a versão com:

```bash
python --version
```

ou:

```bash
python3 --version
```

## Como executar

Entre na pasta do projeto:

```bash
cd dpos-g3-cartel
```

Gere o arquivo de cenários:

```bash
python simulador_dpos.py --gerar-cenarios cenarios.csv
```

Execute a simulação:

```bash
python simulador_dpos.py --cenarios cenarios.csv --saida resultados.csv
```

Fluxo completo:

```bash
python simulador_dpos.py --gerar-cenarios cenarios.csv
python simulador_dpos.py --cenarios cenarios.csv --saida resultados.csv
```

## Gerar resultado com outro nome

Caso não queira sobrescrever o `resultados.csv`, use:

```bash
python simulador_dpos.py --cenarios cenarios.csv --saida resultados_novo.csv
```

## Erro comum no Windows

Se aparecer:

```text
PermissionError: [Errno 13] Permission denied: 'resultados.csv'
```

Provavelmente o arquivo `resultados.csv` está aberto no Excel, LibreOffice, VSCode ou travado pelo OneDrive.

Solução:

1. Feche o arquivo.
2. Rode novamente:

```bash
python simulador_dpos.py --cenarios cenarios.csv --saida resultados.csv
```

Ou gere com outro nome:

```bash
python simulador_dpos.py --cenarios cenarios.csv --saida resultados_novo.csv
```

## Como abrir o CSV no Excel

Os arquivos CSV usam:

```text
Separador: ;
Codificação: utf-8-sig
```

Isso facilita a abertura no Excel em português.

Caso o Excel coloque tudo em uma única célula, importe o CSV manualmente e selecione o separador ponto e vírgula.

## Como interpretar os resultados

Para analisar o `resultados.csv`, observe:

1. Como as métricas mudam quando `tam_cartel` aumenta.
2. Se o efeito do cartel é maior na camada `eleito` do que na camada `stake`.
3. Se a camada `produzido` confirma a concentração observada na eleição.
4. Se comitês maiores reduzem o poder do cartel.
5. Se distribuições de stake mais concentradas tornam o cartel mais forte.

Exemplo de interpretação:

```text
Se o peso do cartel cresce mais na camada eleito do que na camada stake,
isso indica que a eleição amplificou a concentração de poder do cartel.
```

## Como subir no GitHub

Inicialize o repositório:

```bash
git init
```

Adicione os arquivos:

```bash
git add .
```

Crie o commit:

```bash
git commit -m "add: simulador DPoS para analise de cartel"
```

Renomeie a branch principal:

```bash
git branch -M main
```

Adicione o repositório remoto:

```bash
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
```

Envie para o GitHub:

```bash
git push -u origin main
```

## Entrega esperada

A entrega deve conter:

```text
simulador_dpos.py
cenarios.csv
resultados.csv
relatorio.pdf
```

No formulário:

| Campo     | Arquivo             |
| --------- | ------------------- |
| Simulador | `simulador_dpos.py` |
| Cenário   | `cenarios.csv`      |
| Resultado | `resultados.csv`    |
| Relatório | `relatorio.pdf`     |

## Observação sobre o relatório

O relatório deve ser escrito pelo grupo.

Este repositório fornece o código, os cenários e os resultados. A análise final deve explicar:

- a patologia estudada;
- a hipótese do experimento;
- os parâmetros variados;
- as métricas usadas;
- os principais resultados;
- as diferenças entre `stake`, `eleito` e `produzido`;
- o que a patologia revela sobre os limites do DPoS.

## Conclusão esperada

A hipótese é que o cartel tende a concentrar mais poder conforme seu tamanho aumenta, principalmente nas camadas `eleito` e `produzido`.

Se a concentração crescer mais nessas camadas do que na camada `stake`, isso indica que a eleição não apenas reflete a desigualdade inicial, mas também pode amplificá-la.

Esse resultado ajuda a discutir uma limitação do DPoS: embora o sistema seja eficiente por usar poucos produtores, ele pode se tornar politicamente centralizado quando grupos coordenados capturam parte relevante do comitê.
