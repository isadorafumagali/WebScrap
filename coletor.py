import asyncio
import requests
import time
import random
import json
import pathlib
import threading

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from joblib import Parallel, delayed

numero_paginas = 80

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
}

# Pool de fingerprints para variar ao recriar o contexto do Playwright
fingerprints = [
    {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1366, "height": 768},
    },
    {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Safari/605.1.15"
        ),
        "viewport": {"width": 1512, "height": 982},
    },
    {
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1920, "height": 1080},
    },
]

def nome_arquivo_para_link(link):
    slug = link.rstrip("/").split("/")[-1]
    return f"{slug}.json"


#teste inicial
url = "https://saocarlosnotoque.com/"

response = requests.get(url, headers=headers, timeout=60)

print("Página inicial")
print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")


#extração de links
blocos_noticias = soup.select('article[id^="post-"]')

links = []

for bloco in blocos_noticias:
    a = bloco.select_one('h2.entry-title a[href]')
    if a:
        links.append(a["href"])

print("\nLinks encontrados na página inicial:", len(links))

for link in links:
    print(link)


#links de todas as páginas
async def coletar_links_playwright(numero_paginas):

    links_noticias = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        escolha = random.choice(fingerprints)

        context = await browser.new_context(
            user_agent=escolha["user_agent"],
            viewport=escolha["viewport"],
        )

        page = await context.new_page()

        for p_num in range(1, numero_paginas + 1):

            if p_num == 1:
                url = "https://saocarlosnotoque.com/"
            else:
                url = f"https://saocarlosnotoque.com/page/{p_num}/"

            print(f"\nAcessando página {p_num}: {url}")

            sucesso = False

            
            #tentar até 3x por página
            for tentativa in range(1, 4):

                try:
                    print(f"Tentativa {tentativa}/3")

                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )

                    await page.wait_for_timeout(random.randint(1500, 3000))

                    html = await page.content()

                    status = response.status if response else None

                    print(f"Status: {status} | HTML: {len(html)} caracteres")

                    #se for 500 esperar e tentar novamente

                    if status == 500:
                        pathlib.Path(
                            f"debug_page_{p_num}_tentativa{tentativa}.html"
                        ).write_text(html, encoding="utf-8")

                        print("Servidor retornou 500. Aguardando antes de tentar novamente...")

                        await page.wait_for_timeout(random.randint(5000, 10000))
                        continue

                    # se for diferente de 200
                    if status != 200:
                        pathlib.Path(
                            f"debug_page_{p_num}_tentativa{tentativa}.html"
                        ).write_text(html, encoding="utf-8")

                        print(f"Status inesperado: {status}")

                        await page.wait_for_timeout(random.randint(3000, 6000))
                        continue

                    #pra 200
                    soup = BeautifulSoup(html, "html.parser")

                    blocos_noticias = soup.select('article[id^="post-"]')

                    links_pagina = []

                    for bloco in blocos_noticias:
                        a = bloco.select_one('h2.entry-title a[href]')
                        if a:
                            link = a.get("href")
                            if link and link not in links_pagina:
                                links_pagina.append(link)

                    print(f"Notícias encontradas: {len(links_pagina)}")


                    #adicionar novos links
                    novos = 0

                    for link in links_pagina:
                        if link not in links_noticias:
                            links_noticias.append(link)
                            novos += 1

                    print(f"Novos links adicionados: {novos}")

                    sucesso = True
                    break

                except Exception as e:
                    print(f"Erro na tentativa {tentativa}/3: {e}")
                    await page.wait_for_timeout(random.randint(5000, 10000))


            #se as 3 tentativas derem errado
            if not sucesso:
                print(f"ERRO: não foi possível acessar a página {p_num} após 3 tentativas.")

            #pausa entre as páginas
            await page.wait_for_timeout(random.randint(2000, 4000))

            #limpa cookies/sessão e varia fingerprint
            if p_num % 15 == 0:
                print(f"\n--- Recriando contexto do navegador após a página {p_num} ---\n")

                await page.close()
                await context.close()

                escolha = random.choice(fingerprints)

                context = await browser.new_context(
                    user_agent=escolha["user_agent"],
                    viewport=escolha["viewport"],
                )

                page = await context.new_page()

                print(f"Novo fingerprint: {escolha['user_agent'][:50]}... | {escolha['viewport']}")

                await page.wait_for_timeout(random.randint(3000, 6000))

        await browser.close()

    return links_noticias


#executando a coleta
links_noticias = asyncio.run(coletar_links_playwright(numero_paginas))


#resumo dos links
print("\n" + "=" * 60)
print("COLETA DOS LINKS FINALIZADA")
print("=" * 60)

print(f"Total de links encontrados: {len(links_noticias)}")

print("\nPrimeiros links:")
for link in links_noticias[:10]:
    print(link)


#pasta para o json
data_dir = pathlib.Path("data")
data_dir.mkdir(exist_ok=True)



#guardando os erros
erros = []
lock = threading.Lock()


#processando as notícias
class BloqueioOuroCloud(Exception):
    """Erro específico para quando o Ouro.Cloud bloqueia a requisição."""
    pass


#quando uma detecta bloqueio, todas as outras evitam bater na mesma parede ao mesmo tempo.
pausa_global_ate = 0.0
pausa_lock = threading.Lock()

#configurações da pausa longa quando o bloqueio é detectado
PAUSA_BLOQUEIO_MIN_SEGUNDOS = 10 * 60   # 10 minutos
PAUSA_BLOQUEIO_MAX_SEGUNDOS = 20 * 60   # 20 minutos
MAX_TENTATIVAS_BLOQUEIO = 6             # tenta se recuperar do bloqueio até 6 vezes


def aguardar_se_pausa_global_ativa():
    """Se outra thread já sinalizou uma pausa longa em andamento, espera também."""
    with pausa_lock:
        espera = pausa_global_ate - time.time()
    if espera > 0:
        print(f"Aguardando pausa global ativa ({espera/60:.1f} min restantes)...")
        time.sleep(espera)


def registrar_pausa_global(segundos):
    """Marca até quando a pausa global deve durar, para as outras threads respeitarem."""
    global pausa_global_ate
    with pausa_lock:
        novo_fim = time.time() + segundos
        if novo_fim > pausa_global_ate:
            pausa_global_ate = novo_fim


def processar_link(i, link):


    #se já foi processado, pula
    file_path = data_dir / nome_arquivo_para_link(link)
    if file_path.exists():
        return

    ultimo_erro = None
    tentativas_normais = 0
    tentativas_bloqueio = 0
    MAX_TENTATIVAS_NORMAIS = 3

    while tentativas_normais < MAX_TENTATIVAS_NORMAIS:

        aguardar_se_pausa_global_ativa()

        try:
            response = requests.get(link, headers=headers, timeout=60)

            #detecta o bloqueio do Ouro.Cloud mesmo se o status vier 200
            if "ouro-cloud-container" in response.text:
                raise BloqueioOuroCloud("Bloqueado pelo Ouro.Cloud (challenge JS)")

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            #título
            title_tag = soup.find("meta", property="og:title")
            title = title_tag.get("content") if title_tag else None

            #descrição
            description_tag = soup.find("meta", attrs={"name": "description"})
            description = description_tag.get("content") if description_tag else None


            #tags
            tags = [
                tag.get("content")
                for tag in soup.select('meta[property="article:tag"]')
                if tag.get("content")
            ]


            #data
            date_tag = soup.find("meta", property="article:published_time")
            date = date_tag.get("content") if date_tag else None


            #texto da notícia
            texto_materia = soup.find("div", class_="entry-content")

            if texto_materia:
                paragrafos = texto_materia.find_all("p")
                texto = "\n".join(p.get_text(strip=True) for p in paragrafos)
            else:
                texto = None


            #evita salvar registros vazios
            if not title or not texto:
                raise Exception(
                    f"Campos essenciais ausentes (title={bool(title)}, texto={bool(texto)})"
                )

            #organizando as infos
            informacoes = {
                "url": link,
                "titulo": title,
                "descricao": description,
                "tags": tags,
                "texto": texto,
                "data": date,
            }


            #salvando os json
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(informacoes, f, ensure_ascii=False, indent=4)

            print(f"[{i}] Arquivo salvo: {file_path}")
            return  #sucesso, sai da função

        except BloqueioOuroCloud as e:
            ultimo_erro = e
            tentativas_bloqueio += 1

            if tentativas_bloqueio > MAX_TENTATIVAS_BLOQUEIO:
                break  #desiste de vez para esta notícia

            pausa = random.uniform(PAUSA_BLOQUEIO_MIN_SEGUNDOS, PAUSA_BLOQUEIO_MAX_SEGUNDOS)
            registrar_pausa_global(pausa)

            print(
                f"[{i}] BLOQUEIO detectado (tentativa {tentativas_bloqueio}/{MAX_TENTATIVAS_BLOQUEIO}). "
                f"Pausando por {pausa/60:.1f} minutos antes de tentar de novo..."
            )

            time.sleep(pausa)
            #bloqueio não consome uma tentativa normal

        except Exception as e:
            ultimo_erro = e
            tentativas_normais += 1
            print(f"[{i}] Tentativa {tentativas_normais}/{MAX_TENTATIVAS_NORMAIS} falhou: {e}")
            time.sleep(random.uniform(5, 10) * tentativas_normais)  # backoff crescente


    # tratamento de dados, todas as tentativas falharam
    with lock:
        erros.append({"indice": i, "url": link, "erro": str(ultimo_erro)})

    print(f"\nERRO FINAL na notícia {i}\nURL: {link}\nErro: {ultimo_erro}")



#processamento das notícias
print("\n" + "=" * 60)
print("INICIANDO COLETA DAS NOTÍCIAS")
print("=" * 60)

Parallel(n_jobs=1, prefer="threads")(
    delayed(processar_link)(i, link) for i, link in enumerate(links_noticias)
)



#relatório
print("\n" + "=" * 60)
print("COLETA FINALIZADA")
print("=" * 60)

total = len(links_noticias)
quantidade_erros = len(erros)
quantidade_sucesso = total - quantidade_erros

print(f"Total de notícias: {total}")
print(f"Arquivos salvos: {quantidade_sucesso}")
print(f"Erros encontrados: {quantidade_erros}")


#lista de erros
if erros:
    print("\n")
    print("=" * 60)
    print("LISTA DE ERROS")
    print("=" * 60)

    for erro in erros:
        print(f"\nNotícia: {erro['indice']}")
        print(f"URL: {erro['url']}")
        print(f"Erro: {erro['erro']}")
else:
    print("\nNenhum erro encontrado!")
    

import matplotlib.pyplot as plt
import pathlib
import json

data_dir = pathlib.Path("data")

def sanitizar_tags(tags):
    """Retorna a lista de tags formatada (Primeira maiúscula, resto minúsculo).
    Se a lista vier vazia ou nula, usa ['Sem_tag']."""
    if not tags:
        return ["Sem_tag"]
    return [t.strip().capitalize() if t and t.strip() else "Sem_tag" for t in tags]

tag_counter = {}

for json_file in data_dir.rglob("*.json"):
    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
        tags = sanitizar_tags(data.get("tags"))
        for tag in tags:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1

tag_count_dict = dict(sorted(tag_counter.items(), key=lambda x: x[1], reverse=True))

top_tags = list(tag_count_dict.items())[:10]
labels, values = zip(*top_tags)

plt.figure(figsize=(10, 6))
plt.bar(labels, values)
plt.xlabel("Tags")
plt.ylabel("Frequência")
plt.title("Tags Mais Frequentes nos Dados Extraídos")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

from datetime import datetime
import pandas as pd

data_dir = pathlib.Path("data")

records = []

for json_file in data_dir.rglob("*.json"):
    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
        tags = sanitizar_tags(data.get("tags"))
        date_str = data.get("data", "")
        if date_str:
            date = datetime.fromisoformat(date_str)
            month = date.strftime("%Y-%m")
            for tag in tags:
                records.append({"month": month, "tag": tag})

df = pd.DataFrame(records)


def sanitizar_tags(tags):
    if not tags:
        return ["Sem_tag"]
    return [t.strip().capitalize() if t and t.strip() else "Sem_tag" for t in tags]

records = []
for json_file in data_dir.rglob("*.json"):
    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tags = sanitizar_tags(data.get("tags"))
    date_str = data.get("data", "")
    if not date_str:
        continue
    date = datetime.fromisoformat(date_str)
    for tag in tags:
        records.append({
            "date": date,
            "month": date.strftime("%Y-%m"),
            "week": date.strftime("%Y-W%U"),
            "tag": tag,
            "fonte": data.get("fonte"),  # se existir
        })

df = pd.DataFrame(records)

top_n = 15
tag_counts = df["tag"].value_counts().head(top_n)
tag_pct = (tag_counts / len(df) * 100).round(1)

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(tag_counts.index, tag_pct.values)
ax.set_ylabel("% do total de menções")
ax.set_title(f"Top {top_n} Tags Mais Frequentes")
ax.tick_params(axis="x", rotation=45)
for i, v in enumerate(tag_pct.values):
    ax.text(i, v, f"{v}%", ha="center", va="bottom", fontsize=8)
plt.tight_layout()
plt.show()

top_5_geral = df["tag"].value_counts().head(5).index

weekly = (
    df[df["tag"].isin(top_5_geral)]
    .groupby(["week", "tag"])
    .size()
    .unstack(fill_value=0)
    .sort_index()
)

weekly.plot(kind="bar", stacked=True, figsize=(14, 7))
plt.xlabel("Semana")
plt.ylabel("Frequência")
plt.title("Top 5 Tags por Semana")
plt.xticks(rotation=45, ha="right")
plt.legend(title="Tag", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()
plt.show()

import itertools
from collections import Counter

co_occur = Counter()
for json_file in data_dir.rglob("*.json"):
    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tags = sanitizar_tags(data.get("tags"))
    for pair in itertools.combinations(sorted(set(tags)), 2):
        co_occur[pair] += 1

top_pairs = co_occur.most_common(15)
for pair, count in top_pairs:
    print(pair, count)