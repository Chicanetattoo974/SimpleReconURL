<h1 align="center">SRURL - Simple Recon URL v1.0.0</h1>

<p align="center">
  Herramienta de extracción y descubrimiento de URLs para flujos de OSINT y reconocimiento
</p>

<p align="center">
<a href="README.md"><img alt="Português" src="https://img.shields.io/badge/%F0%9F%87%A7%F0%9F%87%B7_Portugu%C3%AAs-757575?style=for-the-badge"></a>
<a href="README_EN.md"><img alt="English" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-757575?style=for-the-badge"></a>
<a href="README_ES.md"><img alt="Español" src="https://img.shields.io/badge/%F0%9F%87%AA%F0%9F%87%B8_Espa%C3%B1ol-1E88E5?style=for-the-badge"></a>
</p>

<h1 align="center">
  <a href="#"><img src="./assets/img/banner.png" width="600px" alt="Simple Recon URL"></a>
</h1>


<p align="center">
<a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10+-1E88E5?style=for-the-badge&logo=python&logoColor=white"></a>
<a href="#"><img alt="Versión" src="https://img.shields.io/badge/Versión-1.0.0-2E7D32?style=for-the-badge&logo=semanticrelease&logoColor=white"></a>
<a href="#"><img alt="Linux" src="https://img.shields.io/badge/Linux-soportado-EF6C00?style=for-the-badge&logo=linux&logoColor=white"></a>
<a href="#"><img alt="macOS" src="https://img.shields.io/badge/macOS-soportado-00838F?style=for-the-badge&logo=apple&logoColor=white"></a>
</p>

<p align="center">
<a href="https://github.com/osintbrazuca/SimpleReconURL/blob/master/LICENSE"><img alt="Licencia" src="https://img.shields.io/github/license/MrCl0wnLab/SimpleReconURL?style=for-the-badge&color=1E88E5&logo=opensourceinitiative&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/graphs/contributors"><img alt="Contribuidores" src="https://img.shields.io/github/contributors-anon/MrCl0wnLab/SimpleReconURL?style=for-the-badge&color=2E7D32&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/issues"><img alt="Issues abiertas" src="https://img.shields.io/github/issues-raw/MrCl0wnLab/SimpleReconURL?style=for-the-badge&color=EF6C00&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/discussions"><img alt="Discusiones" src="https://img.shields.io/github/discussions/MrCl0wnLab/SimpleReconURL?style=for-the-badge&color=6A1B9A&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/network/members"><img alt="Forks" src="https://img.shields.io/github/forks/MrCl0wnLab/SimpleReconURL?style=for-the-badge&color=00838F&logo=github&logoColor=white"></a>
<a href="https://github.com/osintbrazuca/SimpleReconURL/stargazers"><img alt="Estrellas" src="https://img.shields.io/github/stars/MrCl0wnLab/SimpleReconURL?style=for-the-badge&color=F9A825&logo=github&logoColor=white"></a>
</p>

Herramienta de extracción y descubrimiento de URLs para flujos de OSINT y reconocimiento.
A partir de una única URL semilla, obtiene el HTML y extrae todas las URLs alcanzables desde esa página: por defecto solo la propia página, opcionalmente profundizada con un crawler del mismo origen y enriquecida con fuentes externas de descubrimiento (Wayback Machine, Common Crawl, urlscan.io, AlienVault OTX, URLhaus, VirusTotal).

> [!NOTE]
> Construida en Python asíncrono, sin lógica de resolución DNS y sin dependencias de shell externas. Derivada de [SimpleReconSubdomain](https://github.com/MrCl0wnLab/SimpleReconSubdomain), reorientada hacia URLs en lugar de subdominios.

```
Author:   Cleiton Pinheiro aka MrCl0wn
Blog:     https://blog.mrcl0wn.com
GitHub:   https://github.com/MrCl0wnLab
Twitter:  https://twitter.com/MrCl0wnLab
```

---

> [!CAUTION]
> **Aviso legal:** usar SimpleReconURL para atacar objetivos sin consentimiento mutuo previo es ilegal.
> Es responsabilidad del usuario final cumplir todas las leyes municipales, estatales y federales aplicables.
> Los desarrolladores no asumen ninguna responsabilidad por mal uso o daño causado por este programa.

## Índice

- [Instalación](#instalación)
- [Claves de API](#claves-de-api)
- [Uso](#uso)
- [Perfiles](#perfiles)
- [Presets de ejecución](#presets-de-ejecución)
- [Fuentes](#fuentes)
- [Crawler del mismo origen (spider)](#crawler-del-mismo-origen-spider)
- [Rondas recursivas](#rondas-recursivas)
- [Motores de búsqueda](#motores-de-búsqueda)
- [Extracción de rutas Next.js](#extracción-de-rutas-nextjs)
- [Captura con navegador headless](#captura-con-navegador-headless)
- [Extras: URLs externas](#extras-urls-externas)
- [Mapa de enlaces: grafo JSON y visualización HTML](#mapa-de-enlaces-grafo-json-y-visualización-html)
- [Informe Markdown](#informe-markdown)
- [Base de datos: persistencia SQLite](#base-de-datos-persistencia-sqlite)
- [Monitoreo continuo (--watch)](#monitoreo-continuo---watch)
- [Verificación de URLs vivas](#verificación-de-urls-vivas)
- [Formatos de salida](#formatos-de-salida)
- [Encadenando con otras herramientas](#encadenando-con-otras-herramientas)
- [Creando un nuevo módulo](#creando-un-nuevo-módulo)
- [Banners](#banners)

---

## Instalación

```bash
git clone https://github.com/osintbrazuca/SimpleReconURL
cd SimpleReconURL
pip install -r requirements.txt
```

**Dependencias** (`requirements.txt`):

| Paquete | Para qué sirve |
|---|---|
| `httpx[socks]` | Cliente HTTP asíncrono usado por todas las fuentes (`[socks]` habilita `--proxy socks5://`) |
| `beautifulsoup4` | Parseo de HTML en el extractor por defecto, en el crawler `spider` y en `robots_sitemap` |

### Opcional: captura con navegador headless

> [!NOTE]
> La fuente `browser` necesita Playwright y el binario de Chromium (~150MB). **No** es
> necesaria para el resto: sin ella, solo esa fuente se deshabilita sola y todo lo
> demás funciona normalmente.

```bash
pip install -r requirements-browser.txt
playwright install chromium
```

Vea [Captura con navegador headless](#captura-con-navegador-headless) para saber qué hace.

### Docker

Funciona sin necesidad de tener Python instalado. Dos caminos de build, la misma imagen, y los argumentos de la CLI pasan directo:

```bash
# A) a partir del código local (contexto de build = raíz del repositorio)
docker build -t docker/simplereconurl -f docker/Dockerfile .

# B) directo desde GitHub, sin checkout local
docker build -t docker/simplereconurl - < docker/Dockerfile.remote

# ejecución (lo que viene después del nombre de la imagen va a simplereconurl.py)
docker run --rm docker/simplereconurl -u https://target.com/
```

Vea [docker/README_ES.md](docker/README_ES.md) para las opciones completas de build, persistencia de resultados (volumen del `--db`), registro de comandos, jobs del `--watch`, montaje de las claves de API y ejecución del planificador.

---

## Claves de API

> [!IMPORTANT]
> Las claves están en `config/api_keys.json`, que está en el gitignore justamente para
> no ser commiteado por accidente. Nunca versione ese archivo ya completado.

```json
{
    "alienvault_otx": "",
    "brave":          "",
    "publicwww":      "",
    "urlscan":        "",
    "virustotal":     ""
}
```

Complete solo las que tenga. `alienvault_otx` y `urlscan` funcionan sin autenticación (la clave solo aumenta el límite de peticiones); `virustotal`, `brave` y `publicwww` exigen clave, de lo contrario la fuente no devuelve nada.

**Dónde obtener cada clave:**

| Clave | URL |
|---|---|
| `alienvault_otx` | https://otx.alienvault.com, en Settings > API Integration |
| `urlscan` | https://urlscan.io/user/signup |
| `virustotal` | https://www.virustotal.com/gui/join-us |
| `publicwww` | https://publicwww.com/api.html (la exportación de URLs exige plan de pago) |
| `brave` | https://brave.com/search/api/ (tiene tier gratuito) |

---

## Uso

### Básico

```bash
# URL semilla única (el esquema es opcional, asume https://)
python simplereconurl.py -u https://target.com/

# Lista de URLs semilla
python simplereconurl.py -l seeds.txt

# Listar las fuentes disponibles
python simplereconurl.py --list-sources

# Listar los perfiles disponibles (grupos de fuentes predefinidos)
python simplereconurl.py --list-profiles

# Imprimir ejemplos de uso incorporados y salir
python simplereconurl.py --list-examples

# Ejecutar un perfil predefinido (sin escribir la lista de fuentes)
python simplereconurl.py -u https://target.com/ --profile crawl
python simplereconurl.py -u https://target.com/ --profile discovery --verify-live
```

<img src="./assets/img/exemplo-u.png" width="600px" alt="python simplereconurl.py -u https://argentina.gob.ar/">

### Ejemplos en contexto de OSINT

**Bug bounty: mapear la superficie externa de una página**
```bash
python simplereconurl.py -u https://target.com/ \
  --profile discovery --output json --outfile target_urls.json
```

**Crawl profundo de un sitio (solo mismo origen)**
```bash
python simplereconurl.py -u https://target.com/ \
  --sources spider,robots_sitemap \
  --verify-live \
  --output json --outfile crawl.json
```

**Pipeline completo: página semilla + crawl + descubrimiento + verificación de vivas**
```bash
python simplereconurl.py -u https://target.com/ \
  --profile full --verify-live \
  --output json --outfile full.json
```

**Modo silencioso: enviar las URLs directo a otra herramienta**
```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent
```

**Descubrimiento de activos a partir de una lista de URLs semilla**
```bash
python simplereconurl.py -l scope.txt --output json --outfile all_urls.json --timeout 60
```

### Todas las flags

```
Objetivo:
  -u URL                 URL semilla única (esquema opcional, asume https://)
  -l FILE                Archivo con una URL semilla por línea
  --stdin                Lee URLs semilla de la entrada estándar (una por línea); permite uso en pipe

Salida:
  -o {txt,json,csv,ndjson,html,markdown}
                         Formato de salida (por defecto: txt).
                         ndjson   = una línea JSON compacta por URL, ideal para jq
                         html     = mapa de enlaces interactivo (vis-network vía CDN)
                         markdown = informe de reconocimiento legible
  --outfile FILE         Escribe la salida en un archivo
  --network-map          Incluye el grafo de enlaces (nodos/aristas) en la salida JSON.
                         Se activa automáticamente con -o html o --network-html.
  --network-html FILE    Escribe la visualización HTML del mapa de enlaces en FILE, junto
                         con la salida principal. Se combina con cualquier -o.
  --db FILE              Base de resultados por objetivo: persiste la ejecución y sirve de
                         base de comparación. Guarda las URLs descubiertas (con la fuente y,
                         en -v 3, las URLs externas). El registro de comandos está en config/system.db.
  --db-news              Muestra y guarda solo valores inéditos respecto al --db (exige --db)
  --db-list TYPE         Lista y sale: urls | extras (del --db) o history
                         (de config/system.db, sin --db). Acepta filtro -u.

Monitoreo:
  --watch-add CRON       Registra el comando actual (sin el --watch-add) en config/system.db
                         con una programación cron de 5 campos (ej.: "0,15,30,45 * * * *").
  --watch                Ejecuta el daemon planificador: cada minuto dispara en paralelo los
                         jobs vencidos (imprime cada comando). No necesita --db; Ctrl-C termina.
  --watch-list           Lista los jobs registrados con sus IDs y sale.
  --watch-del ID         Elimina el job con el ID indicado (visto en --watch-list).
  --watch-clear          Elimina todos los jobs programados y sale.

Rendimiento:
  -t N                   Multiplicador de concurrencia del --verify-live (por defecto: 8)
  --timeout N            Timeout HTTP en segundos (por defecto: 30)
  --rate-limit N         Máximo de peticiones HTTP simultáneas por fuente (0 = ilimitado)

Red:
  --proxy URL            Enruta todas las peticiones HTTP por un proxy
                         (ej.: http://127.0.0.1:8080 o socks5://host:port)
  --user-agent UA        Sobrescribe el User-Agent de todas las peticiones de las fuentes

Control de fuentes:
  --profile PROFILE      Ejecuta un grupo de fuentes predefinido (fast, crawl, discovery, full).
                         Tiene precedencia sobre --sources.
  --sources LIST         Fuentes separadas por comas (por defecto: todas)
  --exclude LIST         Fuentes a excluir, aplicado después de --sources/--profile
  --recursive N          Rondas de recolección (por defecto: 1, máximo: 20). Cada ronda extra
                         realimenta las URLs recién descubiertas como semillas y ejecuta
                         todas las fuentes seleccionadas sobre ellas. Ninguna fuente se
                         reejecuta sobre una entrada que ya procesó.
  --recursive-max-seeds N
                         Tope de URLs nuevas promovidas a semilla por ronda
                         (por defecto: 500, 0 = sin tope). Los assets nunca se promueven.
  --no-passive           Omite las fuentes pasivas de descubrimiento; la extracción por defecto
                         de la página y las fuentes activas (spider/robots_sitemap) siguen ejecutándose
  --list-sources         Imprime todas las fuentes con sus descripciones y sale
  --list-profiles        Imprime todos los perfiles con sus conjuntos de fuentes y sale
  --list-examples        Imprime los ejemplos de uso incorporados y sale

Preset de ejecución:
  --config FILE          Carga valores por defecto de argumentos desde un archivo JSON.
                         Solo se aplican las claves ausentes en la línea de comandos;
                         las flags explícitas siempre ganan.
                         Plantilla: config/run_config.example.json

Postprocesamiento:
  --verify-live          Sondea cada URL descubierta: estado HTTP, título, servidor,
                         content-length, hash del cuerpo y tiempo de respuesta

Visualización:
  -v [LEVEL]             Nivel de verbosidad 1 a 4 (1=resultados en cero, 2=+códigos HTTP,
                         3=+cuerpo +extras (URLs externas), 4=+excepciones)
  -q, --quiet            Solo resultados; suprime todos los mensajes de proceso
  --no-banner            Suprime el banner y toda la salida de proceso (modo pipe limpio)
  --no-progress          Desactiva la línea de progreso viva de las rondas del
                         --recursive. Solo aparece cuando stderr es una terminal,
                         así que el uso con pipe no cambia de ninguna manera.
  --no-color             Desactiva los colores ANSI
```

---

## Perfiles

Los perfiles son grupos de fuentes predefinidos, declarados en [config/profiles.json](config/profiles.json). Use `--profile NOMBRE` en lugar de escribir listas largas en `--sources`.

```bash
python simplereconurl.py --list-profiles
python simplereconurl.py -u https://target.com/ --profile crawl
```

| Perfil | Descripción | Fuentes |
|---|---|---|
| `fast` | Solo la página semilla, sin ninguna fuente más allá de la extracción por defecto | *(ninguna)* |
| `crawl` | Crawl profundo del mismo origen en el sitio semilla | `spider`, `nextjs` |
| `api` | Superficie de API | `openapi`, `cms_routes`, `well_known` |
| `archive` | Solo archivos históricos de la web | `wayback`, `commoncrawl`, `arquivopt` |
| `search` | Motores de búsqueda | `googlecse`, `yahoo`, `bing`, `google`, `marginalia`, `publicwww` |
| `discovery` | Descubrimiento externo de URLs: archivos, threat intel y búsqueda | `wayback`, `commoncrawl`, `arquivopt`, `urlscan`, `alienvault`, `urlhaus`, `virustotal`, `brave` |
| `browser` | Captura de runtime con navegador headless (necesita Playwright) | `browser` |
| `full` | Todo, excepto `browser` | crawl + robots/sitemap + superficie de API + feeds + todo el descubrimiento |


<img src="./assets/img/list-profiles.png" width="600px" alt="Simple Recon URL">

> [!IMPORTANT]
> `full` es una lista explícita de fuentes, y no `"all"`, justamente para que la fuente `browser`, que exige una descarga opcional de ~150MB, nunca se ejecute de forma implícita. Invóquela con `--profile browser` o `--sources browser`. Al crear una fuente nueva y querer que entre en `full`, agréguela a la lista en [config/profiles.json](config/profiles.json).

Para agregar o editar perfiles, modifique [config/profiles.json](config/profiles.json):

```json
{
  "myprofile": {
    "description": "My custom set",
    "sources": ["spider", "wayback"],
    "options": {"rate_limit": 5}
  }
}
```

---

## Presets de ejecución

Un preset de ejecución es un archivo JSON que guarda valores por defecto de argumentos, permitiendo repetir escaneos sin líneas de comando kilométricas.

```bash
python simplereconurl.py -u https://target.com/ --config config/run_config.example.json
python simplereconurl.py -u https://target.com/ --config my_scan.json
```

**Precedencia (de mayor a menor):**
1. Flags explícitas en la línea de comandos (siempre ganan)
2. Valores del archivo JSON del `--config`
3. Valores por defecto incorporados de argparse

La plantilla comentada en [config/run_config.example.json](config/run_config.example.json) documenta todas las claves disponibles.

---

## Fuentes

```bash
python simplereconurl.py --list-sources
```

La página semilla **siempre** se obtiene y sus URLs se extraen primero. Eso no es una fuente seleccionable: es el comportamiento por defecto de la herramienta y no puede excluirse con `--sources` ni `--exclude`.

### Fuentes pasivas

| Fuente | Exige clave | Observaciones |
|---|---|---|
| `wayback` | No | API CDX de web.archive.org, URLs archivadas bajo el host de la semilla |
| `commoncrawl` | No | API CDX de Common Crawl, recorre los 3 índices de crawl más recientes |
| `arquivopt` | No | Arquivo.pt: archivo web portugués, con cobertura PT/BR fuerte que le falta a Wayback |
| `brave` | Sí | Brave Search API, páginas indexadas por buscador (consulta `site:`) |
| `googlecse` | No | Google vía ~26 Custom Search Engines **públicos**: índice real de Google, sin clave |
| `yahoo` | No | Yahoo Search, el único buscador grande que aún responde `site:` sin desafío |
| `bing` | No | Bing Search: **mejor esfuerzo**, normalmente recibe desafío anti-bot (vea la nota abajo) |
| `google` | No | Scraping de google.com: **mejor esfuerzo**, normalmente bloqueado; use `googlecse` |
| `marginalia` | No | Marginalia: índice independiente y no comercial; páginas únicas, bajo rendimiento en el alcance |
| `publicwww` | Sí | PublicWWW: busca en el **código fuente** de las páginas, no en el texto |
| `urlscan` | Opcional | Límite mayor con clave; URLs de página y de task escaneadas |
| `alienvault` | Opcional | Endpoint `url_list` de AlienVault OTX |
| `urlhaus` | No | Base de URLs maliciosas de URLhaus (abuse.ch), sin autenticación |
| `virustotal` | Sí | Relación `domains/{host}/urls` de VirusTotal |

<img src="./assets/img/list-sources.png" width="600px" alt="Simple Recon URL">


### Fuentes activas

> [!WARNING]
> Las fuentes activas envían peticiones HTTP reales **al objetivo** y quedan registradas
> en sus logs. Úselas solo donde tenga autorización.

| Fuente | Exige clave | Observaciones |
|---|---|---|
| `spider` | No | Crawler BFS del mismo origen + minero de JS/CSS/sourcemap, incluyendo los **endpoints de API relativos** (`/api/v1/users`) que solo existen dentro de los bundles JS |
| `robots_sitemap` | No | Directivas de `robots.txt` + extracción recursiva de los `<loc>` del `sitemap.xml` |
| `nextjs` | No | Extracción de rutas de Next.js: build manifest, RSC flight data, rutas `[param]` y endpoints `/_next/data/` |
| `openapi` | No | Descubrimiento de spec OpenAPI/Swagger, expandiendo `paths{}` en la superficie completa de la API |
| `well_known` | No | Recolección en `.well-known/`: endpoints OIDC, `security.txt` y paths de deep link de apps móviles |
| `cms_routes` | No | Tabla de rutas `/wp-json/` de WordPress + `/jsonapi` de Drupal |
| `feeds` | No | Descubrimiento de feeds RSS/Atom/JSON, con las URLs de las entradas |
| `browser` | No (necesita Playwright) | Navegador headless, captura toda petición que la página hace en runtime |

---

## Crawler del mismo origen (spider)

`spider` parte de la URL semilla exacta (preservando path y query) y hace un crawl en anchura hasta profundidad 3 o 100 páginas, siguiendo `<a href>` y `<link href>`, descargando los archivos JS de `<script src>` y sus sourcemaps, y minando literales de URL dentro de los cuerpos de JS y `.map`.

Por defecto, solo mismo origen: un enlace solo se sigue si el host es igual al de la semilla o un subdominio suyo. Los enlaces de otro origen encontrados en el camino **no se siguen**, pero quedan registrados y aparecen en `-v 3` y en `--db` como URLs externas, siguiendo el mismo patrón que todas las fuentes usan para hallazgos fuera de alcance.

```bash
python simplereconurl.py -u https://target.com/ --sources spider -v 3
```

---

## Rondas recursivas

Por defecto SRURL recolecta una vez y se detiene. Con `--recursive N` el resultado pasa a ser la entrada de la siguiente recolección: las URLs recién descubiertas se convierten en semillas, todas las fuentes seleccionadas vuelven a ejecutarse sobre ellas, y el ciclo se repite hasta N rondas. El valor por defecto es 1, que es exactamente el comportamiento de siempre, y el máximo es 20.

```bash
# tres rondas, con el perfil y las fuentes que ya usa
python simplereconurl.py -u https://target.com/ --profile crawl --recursive 3

# realimentación agresiva, con tope de semillas por ronda
python simplereconurl.py -u https://target.com/ --recursive 10 --recursive-max-seeds 200
```

Cada ronda informa cuánto rindió:

```
[*] Round 2/3: 232 new seed url(s)...
[+] Round 2/3: +1841 urls
[*] Round 3/3: 1602 new seed url(s)...
[+] Round 3/3: +403 urls

[+] Total unique URLs found: 2501 (3 round(s))
[+] 184 asset url(s) found, not crawled (-v 3 to list them)
```

### Progreso en vivo

Una ronda puede tardar minutos. Mientras corre, una única línea se reescribe en el lugar, mostrando cuánto se ha recolectado y cuánto es nuevo:

```
[*] round 2/3 [######----------]  43% | tasks 128/296 | urls 1841 (+412 new) | now /blog/post-1
```

Cada contador lleva etiqueta, porque las dos fracciones miden cosas distintas:

| Campo | Qué es |
|---|---|
| `round 2/3` | ronda actual y el total pedido en `--recursive` |
| `tasks 128/296` | **ejecuciones de fuente** terminadas y agendadas para esta ronda, no URLs |
| `urls 1841` | total único acumulado de toda la ejecución, sumando cada ronda |
| `(+412 new)` | cuántas de esas son inéditas **de esta ronda** |
| `now /blog/post-1` | la URL que se está procesando en ese instante |

El porcentaje es real y no estimado: la herramienta sabe de antemano cuántas ejecuciones tendrá la ronda, porque arma la lista completa antes de disparar. Nada de lo que ya está en pantalla se borra, la línea usa `\r` y se reescribe sobre sí misma.

> [!TIP]
> `tasks` suele ser mucho menor que `semillas × fuentes`, y eso es el dedup por capa trabajando. Las fuentes de capa `host` ya consultaron el dominio entero en la ronda 1, así que no vuelven a ejecutarse y aportan cero ejecuciones aquí.

> [!NOTE]
> La línea va a **stderr**, y solo cuando este es una terminal. En la práctica, `python simplereconurl.py -u https://target.com/ --recursive 3 | httpx` sigue mostrando el progreso en pantalla **y** entrega el pipe limpio, porque solo se redirigió stdout. En cambio `... > log.txt 2>&1` no genera progreso alguno, evitando un archivo lleno de basura de terminal. Use `--no-progress` para apagarlo, o `-q` que suprime todo.

En una terminal estrecha la línea se degrada por prioridad: primero se va la URL, después la barra. Los contadores nunca se van.

### Nada se prueba dos veces

Una URL nunca se vuelve a solicitar en una ronda posterior, y ninguna fuente se reejecuta con una entrada que ya procesó. Esto vale entre rondas, no solo dentro de una.

El punto no evidente es que "entrada ya procesada" significa cosas distintas según la fuente, porque las fuentes no leen la misma parte del objetivo. Cada una declara su capa, visible en la columna `scope` de `--list-sources`:

| Capa | Fuentes | Se ejecuta |
|---|---|---|
| `url` | `page`, `browser` | una vez por URL, ya que leen la página exacta |
| `origin` | `spider`, `nextjs`, `openapi`, `well_known`, `cms_routes`, `feeds` | una vez por origen, ya que sondean rutas fijas del sitio |
| `host` | las 15 pasivas y `robots_sitemap` | una vez por dominio, ya que consultan `*.host` de una sola vez |

> [!IMPORTANT]
> Todos los módulos seleccionados siguen ejecutándose. Lo que la herramienta evita es repetir una ejecución cuyo resultado sería idéntico. Consultar Wayback 257 veces con la misma query no devuelve ninguna URL adicional, y en una prueba con un objetivo de 61 URLs esto redujo 1403 ejecuciones de fuente a 151, sin perder un solo resultado.

Un subdominio nuevo descubierto por el camino cuenta como origen nuevo, así que las fuentes de capa `origin` sí se ejecutan de nuevo para él.

### Semillas y límites

Solo las URLs que pueden contener enlaces se convierten en semillas. Los assets se descartan por extensión (`.css`, `.js`, `.png`, `.woff2`, `.pdf` y similares), porque el extractor de página solo analiza HTML. Los bundles JS los sigue minando `spider`, que es el módulo hecho para eso.

**Esos assets no se pierden.** Siguen en la lista de URLs del resultado como cualquier otro hallazgo; lo que la herramienta ahora informa es cuáles fueron encontrados sin haber sido visitados nunca. Al final aparece el conteo, y en `-v 3` la lista completa entra en la salida, en un bloque propio:

```
## Extras
### External URLs (out of scope, not followed)
### Asset URLs (in scope, found but not crawled)
```

> [!TIP]
> Los dos bloques son cosas distintas y por eso se mantienen separados. Las externas están **fuera** del alcance y **no** constan en la lista principal. Los assets están **dentro** del alcance y **ya** constan en ella: la única información nueva es que no fueron solicitados. Por eso el bloque de assets aparece en el JSON, en el informe markdown y en el `--db` (tipo `url_asset`), pero nunca se anexa a las salidas `csv`, `ndjson` y `txt`, donde generaría una segunda línea para la misma URL.

> [!WARNING]
> La recursión multiplica el tráfico enviado al objetivo. `--recursive-max-seeds` (por defecto 500) limita cuántas URLs nuevas pasan a semilla por ronda, y conviene ajustarlo junto con `--rate-limit` antes de subir mucho el N. Un valor fuera del rango 1 a 20 termina la ejecución con código 2, en lugar de ser ajustado en silencio.

La recursión se detiene sola cuando se acaban las semillas nuevas, aunque no se haya agotado N.

---

## Motores de búsqueda

Los buscadores conocen URLs que ninguna otra fuente alcanza: páginas enlazadas únicamente desde sitios de terceros, que ni un snapshot de archivo ni un crawl del mismo origen encuentran. Todos los módulos envían una única consulta `site:{host}` y paginan los resultados.

```bash
python simplereconurl.py -u https://target.com/ --profile search
python simplereconurl.py -u https://target.com/ --sources googlecse,yahoo -v 1
```

**Cuáles funcionan realmente** (medido, no supuesto):

| Fuente | Clave | Situación |
|---|---|---|
| `googlecse` | ninguna | Funciona. Alcanza el índice real de Google a través de ~26 Custom Search Engines **públicos**. Rota 3 por ejecución, ya que cada uno tiene índice y alcance propios. |
| `yahoo` | ninguna | Funciona. Aún responde `site:` sin desafío. Pagina 4 offsets, verificados como conjuntos distintos, no la misma página repetida. |
| `marginalia` | ninguna | Funciona. Índice independiente que nadie más tiene. Pero es una **búsqueda en texto libre, no `site:`**: medidos de 1 a 3 aciertos en el objetivo por cada 20, y bloquea tras unas 3 consultas. Poco volumen, cobertura única. |
| `publicwww` | obligatoria | Busca en el **código fuente** de las páginas en lugar del texto, así que encuentra las páginas del objetivo por un fragmento compartido (ID de Analytics, nombre de bundle). La exportación de URLs exige plan de pago. |
| `bing` | ninguna | Mejor esfuerzo. Devolvió desafío Cloudflare Turnstile y **cero** resultados en las pruebas, incluso con headers de navegador. |
| `google` | ninguna | Mejor esfuerzo. `google.com/search` devolvió una página cáscara de JavaScript con **cero** enlaces de resultado. Use `googlecse` para cobertura de Google. |

> [!TIP]
> Para cobertura de Google use `googlecse`: alcanza el índice real a través de Custom
> Search Engines públicos y no depende de scraping, que hoy viene bloqueado.

`bing` y `google` siguen en el proyecto porque el bloqueo es por IP y reputación, no permanente. Pueden funcionar desde otra red o detrás de `--proxy`. Cuando están bloqueados no aportan nada y nunca rompen la ejecución, así que ver `0 new urls` viniendo de ellos es el resultado esperado, no un defecto.

Dos notas de implementación que vale conocer:

- **El User-Agent por defecto de la herramienta es bloqueo inmediato aquí.** Estos módulos rotan un UA realista de navegador de escritorio, salvo que usted defina `--user-agent` explícitamente, en cuyo caso se respeta el suyo.
- **La navegación del propio buscador se filtra.** Raspar una página de resultados también recoge los enlaces de cabecera y pie; una sola consulta a Bing aportó 61 URLs basura de `r.bing.com` antes de que ese filtro existiera. Los enlaces dentro del alcance del objetivo nunca se descartan, así que escanear uno de esos dominios sigue funcionando.

---

## Extracción de rutas Next.js

Una aplicación Next.js guarda la tabla de rutas entera dentro del bundle JS, no en el HTML. Los chunks minificados contienen arrays como

```js
["/[username]/[contractAddress]/[tokenId]/bid", "/admin/approve", "/settings", ...]
```

que enumeran todas las páginas del sitio, incluidas áreas administrativas y rutas dinámicas enlazadas desde ningún lado.

```bash
python simplereconurl.py -u https://target.com/ --sources nextjs -v 1
python simplereconurl.py -u https://target.com/ --profile crawl      # spider + nextjs
```

El framework tiene dos routers que exponen cosas completamente distintas, y ambos están cubiertos:

| Router | Qué entrega |
|---|---|
| **Pages Router** (heredado, común en objetivos pequeños) | `__NEXT_DATA__` lleva al `buildId`; el `/_next/static/<buildId>/_buildManifest.js`, cuyas claves son la **tabla de rutas completa**; y los endpoints JSON `/_next/data/<buildId>/<ruta>.json` por ruta, frecuentemente sin autenticación |
| **App Router** (Next 13+, lo que usa la mayoría de los sitios) | RSC flight data (`self.__next_f.push`) incrustado en el HTML. No hay `__NEXT_DATA__` ni build manifest |

Las plantillas de ruta (`/[username]/...`, `/blog/[...slug]`) se emiten tal cual. No son URLs consultables, pero son la superficie de rutas, que es justamente el punto. La misma decisión que toma `openapi` para `/users/{id}`.

La detección cuesta una única petición: si la página semilla no muestra el marcador `/_next/`, `__NEXT_DATA__` o `self.__next_f`, el módulo lo avisa en `-v 1` y se detiene sin sondear nada.

> [!NOTE]
> La fuente `spider` también mina paths relativos del JS y ahora entiende segmentos `[param]`, así que capta rutas dinámicas en cualquier framework. `nextjs` va más allá, con los artefactos específicos del framework (build manifest, buildId, endpoints `/_next/data/`). Ejecutar ambos descarga algunos chunks dos veces, algo aceptado, ya que no existe caché entre fuentes.

---

## Captura con navegador headless

Todas las demás fuentes leen **markup o texto estático**. La fuente `browser` abre la URL semilla en una instancia oculta de Chromium y registra toda petición que la página realmente hace **en runtime**: llamadas `fetch`/XHR, scripts inyectados por JS, beacons de rastreo, recursos con carga tardía y handshakes de WebSocket. Nada de eso existe en el HTML, así que ningún parseo lo encontraría.

```bash
# preparación única
pip install -r requirements-browser.txt && playwright install chromium

python simplereconurl.py -u https://target.com/ --profile browser
python simplereconurl.py -u https://target.com/ --sources browser -v 2   # registra método + tipo de recurso
```

La diferencia en una página cuyos endpoints se llaman desde JavaScript:

```
# parseo estático (--profile fast)
http://target/static-link.html

# captura con navegador (--profile browser)
http://target/
http://target/api/v1/users?page=1        <- fetch()
http://target/api/v1/config.json         <- fetch()
http://target/api/v1/late-call           <- fetch() disparado 400ms después del load
http://target/assets/injected-by-js.js   <- <script> insertado por JS
http://target/beacon.gif?t=1786253769401 <- URL generada en runtime
http://target/static-link.html
```

Cómo se comporta:

- **Siempre headless**: la ventana del navegador nunca aparece.
- **El alcance** sigue la misma regla que todas las fuentes: las peticiones dentro del alcance se vuelven resultado; los hosts de terceros (CDNs, analytics, fuentes tipográficas) van a URLs externas, visibles en `-v 3` y en `--db`.
- **Espera el tráfico tardío**: después del `load`, aguarda a que la red quede inactiva (con límite, para que páginas con polling o WebSocket no la cuelguen), y luego desplaza la página una vez para disparar las peticiones de carga tardía.
- **Falla de forma suave**: un timeout de navegación o un host inalcanzable aún devuelven lo capturado antes del fallo, y el navegador siempre se cierra.
- **Respeta `--timeout`, `--proxy` y `--user-agent`** como el resto de la herramienta.
- Sin Playwright instalado, imprime una sugerencia de instalación y devuelve vacío; nunca rompe la ejecución.

No entra en `--profile full` a propósito. Vea la nota en [Perfiles](#perfiles).

---

## Extras: URLs externas

El nivel de verbosidad **`-v 3`** revela las URLs recogidas durante la enumeración que quedan fuera del host de la semilla, útil para mapear dependencias de terceros y entender hacia dónde apunta la página. (El nivel 3 también activa el log de vista previa del cuerpo HTTP.)

```bash
python simplereconurl.py -u https://target.com/ --sources spider -v 3 --no-banner
```

### Salida por formato

**txt**: sección agregada al final (suprimida con `--no-banner`/`--quiet`):
```
https://target.com/
https://target.com/about

# External URLs
https://accounts.google.com/o/oauth2/...
https://cdn.jsdelivr.net/npm/...
```

**json**: objeto `"extras"` en el nivel superior:
```json
"extras": {
  "urls_external": ["https://accounts.google.com/...", "https://cdn.jsdelivr.net/..."]
}
```

**ndjson**: líneas adicionales con el campo `type`:
```json
{"seed": "https://target.com/", "url": "https://cdn.jsdelivr.net/...", "type": "url_external"}
```

**csv**: filas extra con `type` = `url_external`.

### Recetas de jq para los extras

```bash
python simplereconurl.py -u https://target.com/ --sources spider -v 3 -o ndjson \
  | jq 'select(.type == "url_external") | .url'
```

---

## Mapa de enlaces: grafo JSON y visualización HTML

Transforma la lista plana de URLs en un grafo navegable: un grafo JSON (nodos + aristas) que puede enviar a otras herramientas, y una página HTML interactiva para triaje visual. El grafo se construye **enteramente a partir de datos ya recogidos** en la ejecución, sin peticiones extra.

### Referencia de las flags: tres ejes

| Flag | Papel | La salida va a | ¿Combina? |
|---|---|---|---|
| **`-o html`** | Formato principal de salida, reemplaza `txt`/`json`/`csv`/`ndjson` | `stdout` o `--outfile` | Un `-o` por vez |
| **`--network-html FILE`** | Artefacto paralelo, siempre escribe la visualización HTML en `FILE` | `FILE` (cualquier ruta) | Sí, funciona junto a cualquier `-o` |
| **`--network-map`** | Inyecta un bloque `"network"` (nodos/aristas) en la salida JSON | Dentro del documento JSON | Solo tiene sentido con `-o json`; se activa automáticamente con `-o html`/`--network-html` |

```bash
python simplereconurl.py -u https://target.com/ --profile full --network-map -o json --outfile out.json
python simplereconurl.py -u https://target.com/ --profile full -o html --outfile map.html
```

### Modelo del grafo

| Tipo de nodo | Construido a partir de | Observaciones |
|---|---|---|
| `seed` | objetivo del escaneo | uno por URL semilla |
| `page` | `result.urls` | coloreado por `live.status` (2xx/3xx/4xx/5xx/ninguno) |
| `external` | `extras.urls_external` (necesita `-v 3`) | URLs fuera de alcance encontradas pero no seguidas |

| Relación de la arista | Dirección |
|---|---|
| `links_to` | `seed > page` |
| `links_to_external` | `seed > external` |

Esto representa "lo que se encontró a partir de esta semilla", no un grafo literal de página a página; las fuentes informan qué URLs encontraron, no qué página enlazó a cuál.

### Visualizador HTML

Archivo único y autocontenido. Carga [vis-network](https://visjs.github.io/vis-network/) `9.1.9` desde `unpkg.com` (CDN, así que necesita internet al abrirlo). Haga clic en un nodo para ver estado HTTP, título y servidor; todas las semillas de una ejecución con múltiples objetivos se fusionan en un único grafo.

---

## Informe Markdown

`-o markdown` produce un informe completo de reconocimiento en un único archivo `.md`: métricas de resumen, tabla de URLs vivas, detección de cuerpos de respuesta duplicados, la lista completa de URLs, los extras de URLs externas y la contribución de cada fuente.

```bash
python simplereconurl.py -u https://target.com/ --verify-live -o markdown --outfile report.md
```

---

## Base de datos: persistencia SQLite

Persiste cada ejecución en un archivo SQLite, compara los hallazgos con ejecuciones anteriores y permite leer los datos de vuelta, todo con el `sqlite3` de la biblioteca estándar de Python, sin dependencia extra. Son **dos** almacenamientos:

- **Base de resultados por objetivo**: `--db FILE` (la ruta la elige usted). Guarda **solo resultados**: las `urls` descubiertas (marcadas con la fuente y campos opcionales de verificación) y los `extras` (URLs externas, en `-v 3`). Archivos distintos son almacenamientos independientes.
- **Base de sistema fija**: `config/system.db` (resuelta respecto a la instalación y **nunca pasada por parámetro**). Guarda el registro histórico de comandos y los jobs del planificador `--watch`.

```bash
# Guardar la ejecución completa
python simplereconurl.py -u https://target.com/ --db recon.db

# Solo lo nuevo desde la última ejecución
python simplereconurl.py -u https://target.com/ --db recon.db --db-news

# Inspeccionar la base
python simplereconurl.py --db recon.db --db-list urls
python simplereconurl.py --db recon.db --db-list extras
python simplereconurl.py --db-list history

# Enviar las URLs almacenadas a otra herramienta
python simplereconurl.py --db recon.db --db-list urls | httpx -silent
```

### Esquema

Solo inserción, indexado por `seed`.

| Tabla | Contenido |
|---|---|
| `urls` | URLs descubiertas + fuente + campos opcionales de la verificación (status, title, server, body_hash, response_ms) |
| `extras` | URLs externas (fuera de alcance), guardadas en `-v 3` |

---

## Monitoreo continuo (`--watch`)

Un planificador cron incorporado: registre los comandos de reconocimiento una vez y ejecute un daemon que los dispara según la programación. Los jobs quedan en el `config/system.db` fijo, sin necesitar `cron` ni `systemd` externos.

```bash
# cada 15 minutos, ejecuta un escaneo de descubrimiento que persiste resultados y hace el diff
python simplereconurl.py -u https://target.com/ --profile discovery --db target.db --quiet \
  --watch-add "0,15,30,45 * * * *"

# ejecuta el planificador
python simplereconurl.py --watch

# gestiona los jobs
python simplereconurl.py --watch-list
python simplereconurl.py --watch-del 3
python simplereconurl.py --watch-clear
```

---

## Verificación de URLs vivas

`--verify-live` sondea cada URL descubierta directamente (ya lleva su propio esquema; un fallo de conexión reintenta una vez con el otro esquema) y registra estado HTTP, título, header de servidor, content length, un hash del cuerpo y el tiempo de respuesta.

```bash
python simplereconurl.py -u https://target.com/ --verify-live -o json --outfile out.json
```

```
[LIVE] https://target.com/about → 200 - About Us
[LIVE] https://target.com/old-page → 404
```

El campo `duplicate_bodies` en la salida JSON marca las URLs que comparten el mismo hash de cuerpo de respuesta, útil para identificar soft-404 o páginas de contenido duplicado.

<img src="./assets/img/exemplo-live.png" width="600px" alt="python simplereconurl.py -u https://argentina.gob.ar/">

---

## Formatos de salida

### Terminal (por defecto)

```
------------------------------------------------------------
[*] Enumerating: https://target.com/
------------------------------------------------------------
[*] Extracting URLs from the seed page...
[*] [page] +12 urls
[*] [spider] +34 urls
[*] [wayback] +8 urls

[+] Total unique URLs found: 41

https://target.com/
https://target.com/about
https://target.com/blog/post-1
...
```

### JSON

```json
{
  "seed": "https://target.com/",
  "timestamp": "2026-05-27T14:32:01.123456",
  "total": 41,
  "urls": ["https://target.com/", "https://target.com/about"],
  "live_urls": {
    "https://target.com/about": {
      "status": 200,
      "title": "About Us",
      "server": "nginx/1.24.0",
      "content_length": 1842,
      "body_hash": "a1b2c3d4e5f6a7b8",
      "response_ms": 125
    }
  },
  "sources": {"page": 12, "spider": 34, "wayback": 8}
}
```

### CSV

```
seed,url,type,source,status,title,server,body_hash,response_ms
https://target.com/,https://target.com/about,url,spider,200,About Us,nginx/1.24.0,a1b2c3d4e5f6a7b8,125
```

### NDJSON

Una línea JSON compacta por URL, pensada para streaming y para encadenar con `jq`.

```json
{"seed": "https://target.com/", "url": "https://target.com/about", "type": "url", "source": "spider", "status": 200, "title": "About Us"}
```

```bash
# Solo URLs vivas
python simplereconurl.py -u https://target.com/ --verify-live -o ndjson | jq 'select(.status != null)'

# Extraer solo las URLs (listo para pipe)
python simplereconurl.py -u https://target.com/ -o ndjson | jq -r '.url'
```

### TXT

```bash
python simplereconurl.py -u https://target.com/ -o txt --outfile results/target.txt
```

### HTML: mapa de enlaces interactivo

Vea [Mapa de enlaces](#mapa-de-enlaces-grafo-json-y-visualización-html).

### Markdown: informe de reconocimiento legible

Vea [Informe Markdown](#informe-markdown).

---

## Encadenando con otras herramientas

### httpx, sondeo HTTP

```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent -status-code -title -tech-detect
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent -mc 200
```

### nuclei, escaneo de vulnerabilidades

```bash
python simplereconurl.py -u https://target.com/ --no-banner \
  | httpx -silent \
  | nuclei -t cves/ -silent
```

### katana / gau, crawling adicional

```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | katana -silent
python simplereconurl.py -u https://target.com/ --no-banner | gau --threads 10
```

### gowitness / aquatone, capturas de pantalla

```bash
python simplereconurl.py -u https://target.com/ --no-banner | httpx -silent | gowitness scan single
python simplereconurl.py -u https://target.com/ --no-banner | aquatone -out aquatone-report/
```

### string-x (strx): enriquecimiento y automatización

[string-x](https://github.com/MrCl0wnLab/string-x) es una herramienta modular de automatización que usa el placeholder `{STRING}`. Se combina naturalmente con SimpleReconURL vía pipe.

```bash
# Sondeo HTTP en todas las URLs descubiertas
python simplereconurl.py -u https://target.com/ --no-banner \
  | strx -st "echo {STRING}" -module "clc:http_probe" -pm

# Extrae correos de cada página descubierta
python simplereconurl.py -u https://target.com/ --no-banner \
  | strx -st "curl -sk {STRING}" -module "ext:email" -pm

# Notifica en Telegram cada URL recién descubierta
python simplereconurl.py -u https://target.com/ --db recon.db --db-news --no-banner \
  | strx -st "echo {STRING}" -module "con:telegram" -pm
```

---

## Creando un nuevo módulo

Todas las fuentes heredan de `BaseSource`, en `sources/base.py`. Basta con colocar el archivo en `sources/passive/` o `sources/active/`, ningún otro archivo necesita edición.

El nombre de la clase debe ser el **nombre del archivo con inicial mayúscula** (por ejemplo, `myservice.py` da la clase `Myservice`), y `NAME` tiene que ser igual al nombre del archivo sin el `.py`.

El `fetch(target)` de una fuente recibe un `Target` (`target.url` es la URL completa de la semilla, `target.host` es el hostname en minúsculas) y devuelve las **URLs** dentro del alcance que encontró. Pase siempre los hallazgos crudos por `self._filter_urls(urls, target.host)`, que conserva las URLs dentro del alcance y enruta automáticamente las de fuera hacia `self.extras['urls_external']`.

### Nueva fuente pasiva (consulta por dominio)

```python
# sources/passive/myservice.py
from sources.base import BaseSource, Target
from core.config import get_key


class Myservice(BaseSource):
    NAME = 'myservice'
    DESCRIPTION = 'My custom service'
    API_TOKEN_IS_REQUIREMENT = True

    async def fetch(self, target: Target) -> set[str]:
        api_key = get_key('myservice')
        if not api_key:
            return set()

        urls: set[str] = set()
        headers = {'Authorization': f'Bearer {api_key}'}
        async with self._make_client(headers=headers) as client:
            resp = await self._get(client, f'https://api.myservice.com/urls/{target.host}')
            if resp.status_code == 200:
                for entry in resp.json().get('data', []):
                    if entry.get('url'):
                        urls.add(entry['url'])

        return self._filter_urls(urls, target.host)
```

Agregue la clave a `config/api_keys.json`:
```json
{ "myservice": "your-api-key-here" }
```

### Nueva fuente activa (HTTP directo)

```python
# sources/active/myactive.py
from sources.base import BaseSource, Target


class Myactive(BaseSource):
    NAME = 'myactive'
    DESCRIPTION = 'Active: custom URL probe'
    API_TOKEN_IS_REQUIREMENT = False

    async def fetch(self, target: Target) -> set[str]:
        urls: set[str] = set()
        try:
            async with self._make_client(verify=False) as client:
                resp = await self._get(client, target.url)
                # ... parse resp.text for URLs ...
        except Exception as e:
            self._log_exc(e)
        return self._filter_urls(urls, target.host)
```

---

## Banners

El arte de inicio se sortea **aleatoriamente** en cada ejecución, siguiendo el mismo esquema de [string-x](https://github.com/MrCl0wnLab/string-x). Cada banner es un archivo `.txt` en [core/banner/asciiart/](core/banner/asciiart/), y debajo se imprime un pie fijo con nombre de la herramienta, versión y enlaces del autor.

Para agregar un banner, basta con colocar un `.txt` en ese directorio. Nada más necesita edición:

```bash
cp my-art.txt core/banner/asciiart/
```

Reglas para los archivos de banner:

- **ANSI crudo, no markup de Rich.** Los colores deben estar incrustados como códigos de escape reales (`ESC[0;91m ... ESC[0m`). Esa es la única diferencia deliberada respecto a string-x, que guarda etiquetas `[color]...[/color]` y las renderiza con la biblioteca `rich`. Aquí los archivos se imprimen tal cual, así que el proyecto no necesita dependencia extra. Con `--no-color` (o cuando la salida va a un pipe), los escapes se eliminan automáticamente.
- **Dos placeholders** se sustituyen al momento de mostrar, ambos provenientes de [core/settings.py](core/settings.py):

  | Placeholder | Se vuelve |
  |---|---|
  | `[VERSION]` | `1.0.0` |
  | `[DESCRIPTION]` | `Extract and discover URLs from a seed page` |

- Mantenga el arte razonablemente estrecho; no existe filtro por ancho de terminal, así que un arte muy ancho se rompe en terminales estrechos.

Dónde aparece el banner:

| Comando | Banner |
|---|---|
| Ejecución normal, `--help`/`-h`, `--list-sources`, `--list-profiles`, `--list-examples`, invocación sin argumentos | sí |
| `-q` / `--quiet` / `--no-banner` (cualquier comando) | no |
| `--db-list` | no, porque emite líneas de datos listas para pipe, y así sigue siendo seguro para `\| httpx` |

Un directorio de banners ausente, vacío o ilegible no es un error: la herramienta simplemente imprime el pie solo y sigue adelante.

<img src="./assets/img/list-examples.png" width="600px" alt="Ejemplos">

---

## 📄 LICENCIA

Este proyecto está licenciado bajo la Licencia Apache. Vea el archivo [LICENSE](LICENSE) para más detalles.

## 👨‍💻 AUTOR

**MrCl0wn**
- 🌐 **Blog**: [http://blog.mrcl0wn.com](http://blog.mrcl0wn.com)
- 🐙 **GitHub**: [@MrCl0wnLab](https://github.com/MrCl0wnLab)
- 🐦 **Twitter**: [@MrCl0wnLab](https://twitter.com/MrCl0wnLab)
- 📧 **Email**: mrcl0wnlab\@\gmail.com

---

## Contribuciones ✨ <a name="contribuciones"></a>

¡Las contribuciones de cualquier tipo son bienvenidas!

<a href="https://github.com/osintbrazuca/SimpleReconURL/graphs/contributors">
  <img src="https://contributors-img.web.app/image?repo=osintbrazuca/SimpleReconURL&max=500" alt="Lista de contribuidores" width="100%"/>
</a>

---

<div align="center">

**⭐ ¡Si este proyecto le fue útil, considere dejar una estrella!**

**💡 ¡Sugerencias y comentarios siempre son bienvenidos!**

**💀 Hacker Hackeia!**

</div>
