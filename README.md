# WebScrap

Coletor de notícias do portal [São Carlos no Toque](https://saocarlosnotoque.com/) com análise exploratória das tags mais frequentes. O projeto percorre as páginas de listagem do site, extrai título, descrição, tags, data e texto de cada matéria, salva tudo em JSON e gera gráficos a partir do material coletado.

## O que o projeto faz

1. **Coleta de links**: usa o [Playwright](https://playwright.dev/python/) (Chromium headless) para navegar pelas páginas de listagem (`/page/N/`) e reunir os links das notícias. Cada página tem até 3 tentativas, com pausas aleatórias, e o contexto do navegador é recriado a cada 15 páginas com um novo *fingerprint* (user-agent e viewport).
2. **Extração das notícias**: para cada link, usa `requests` + `BeautifulSoup` para ler os metadados (`og:title`, `description`, `article:tag`, `article:published_time`) e o texto do corpo (`div.entry-content`).
3. **Resiliência**: tenta novamente com *backoff* crescente em caso de falha. Quando o site responde com um desafio JavaScript de bloqueio (Ouro.Cloud), todas as threads entram em uma pausa global de 10 a 20 minutos. Notícias já baixadas são puladas, então a coleta pode ser retomada.
4. **Análise**: conta e visualiza as tags mais frequentes, a evolução semanal das principais tags e as coocorrências entre tags.

## Estrutura do repositório

```
WebScrap/
├── coletor.py                      # coleta + análise (script único)
├── data/                           # uma notícia por arquivo .json
├── tags_mais_frequentes.png        # gráfico: top tags (contagem)
├── frequencia_tag_1199.png         # gráfico: tags em % do total de menções
├── tags_por_semana.png             # gráfico: top 5 tags por semana
└── noticias_mais_frequentes_1199.png
```

## Dados coletados

O diretório `data/` contém **1.199 notícias**, publicadas entre **26/07/2026 e 15/09/2026**. Cada arquivo tem o nome derivado do final da URL da matéria e a seguinte estrutura:

```json
{
    "url": "https://saocarlosnotoque.com/...",
    "titulo": "Título da notícia",
    "descricao": "Resumo da matéria (meta description)",
    "tags": ["Tag 1", "Tag 2"],
    "texto": "Parágrafos da matéria separados por quebra de linha",
    "data": "2026-09-15T20:19:55-03:00"
}
```

Notícias sem tags são tratadas como `Sem_tag` na análise.

## Requisitos

- Python 3.9+
- Bibliotecas: `requests`, `beautifulsoup4`, `playwright`, `joblib`, `matplotlib`, `pandas`

## Instalação

```bash
git clone https://github.com/isadorafumagali/WebScrap.git
cd WebScrap

pip install requests beautifulsoup4 playwright joblib matplotlib pandas
playwright install chromium
```

## Como usar

```bash
python coletor.py
```

O script executa, em sequência, a coleta dos links, o download das notícias para `data/` e as análises com gráficos (exibidos com `plt.show()`).

### Configuração

| Parâmetro | Onde | Padrão | Descrição |
|---|---|---|---|
| `numero_paginas` | topo do `coletor.py` | `80` | Quantidade de páginas de listagem a percorrer |
| `n_jobs` | `Parallel(...)` | `1` | Número de threads na extração das notícias |
| `PAUSA_BLOQUEIO_MIN/MAX_SEGUNDOS` | `coletor.py` | 10 e 20 min | Duração da pausa ao detectar bloqueio |
| `MAX_TENTATIVAS_BLOQUEIO` | `coletor.py` | `6` | Tentativas de recuperação após bloqueio |

## Análises geradas

- **Tags mais frequentes**: top 10 em contagem absoluta e top 15 em percentual do total de menções.
- **Top 5 tags por semana**: barras empilhadas ao longo do tempo.
- **Coocorrência de tags**: os 15 pares de tags que mais aparecem juntos na mesma notícia (impresso no terminal).

## Uso responsável

Este projeto foi feito para fins de estudo. Ao rodá-lo, respeite os termos de uso e o `robots.txt` do site, mantenha os intervalos entre requisições e evite aumentar o paralelismo de forma agressiva. O conteúdo das notícias pertence aos seus respectivos autores e ao portal de origem.

## Autora

Isadora Fumagali — [@isadorafumagali](https://github.com/isadorafumagali)