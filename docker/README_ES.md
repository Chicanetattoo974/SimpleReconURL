# Docker

<p align="center">
<a href="README.md"><img alt="Português" src="https://img.shields.io/badge/%F0%9F%87%A7%F0%9F%87%B7_Portugu%C3%AAs-757575?style=for-the-badge"></a>
<a href="README_EN.md"><img alt="English" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-757575?style=for-the-badge"></a>
<a href="README_ES.md"><img alt="Español" src="https://img.shields.io/badge/%F0%9F%87%AA%F0%9F%87%B8_Espa%C3%B1ol-1E88E5?style=for-the-badge"></a>
</p>

Ejecuta SimpleReconURL en un contenedor, sin necesidad de tener Python instalado.

## Build

Son dos caminos de build, y ambos producen la misma imagen `docker/simplereconurl`.

### Opción A: a partir del código local (`docker/Dockerfile`)

Haga el build desde la **raíz del repositorio** (el contexto debe incluir el proyecto entero):

```bash
docker build -t docker/simplereconurl -f docker/Dockerfile .
```

### Opción B: directo desde GitHub (`docker/Dockerfile.remote`)

No necesita checkout local. Este Dockerfile clona el proyecto solo, así que el contexto de build se ignora:

```bash
# con un contexto descartable
docker build -t docker/simplereconurl -f docker/Dockerfile.remote .

# sin contexto alguno (enviando el Dockerfile por el pipe)
docker build -t docker/simplereconurl - < docker/Dockerfile.remote

# sin nada clonado, construyendo desde la URL cruda
curl -sSL https://raw.githubusercontent.com/osintbrazuca/SimpleReconURL/master/docker/Dockerfile.remote \
  | docker build -t docker/simplereconurl -
```

Para fijar una rama, tag o fork, use build args:

```bash
docker build -t docker/simplereconurl -f docker/Dockerfile.remote \
  --build-arg REF=v1.0.0 \
  --build-arg REPO_URL=https://github.com/osintbrazuca/SimpleReconURL.git .
```

## Ejecución

Todo lo que venga después del nombre de la imagen se pasa directo a `python simplereconurl.py`:

```bash
# El ejemplo principal
docker run --rm docker/simplereconurl -u https://target.com/

# Sin argumentos -> ayuda
docker run --rm docker/simplereconurl

# Listar fuentes / perfiles / ejemplos
docker run --rm docker/simplereconurl --list-sources
docker run --rm docker/simplereconurl --list-profiles

# Listo para pipe (la salida fuera de TTY sale sin color automáticamente)
docker run --rm docker/simplereconurl -u https://target.com/ --no-banner | httpx -silent

# Salida interactiva y coloreada
docker run --rm -it docker/simplereconurl -u https://target.com/ --profile crawl
```

## Persistiendo datos (resultados, registro de comandos, jobs del watch)

> [!WARNING]
> Con `--rm` el contenedor es efímero y todo lo que escribió se descarta al terminar.
> Monte un directorio del host y apunte el `--db` hacia él para conservar los resultados.

```bash
mkdir -p data
docker run --rm -v "$PWD/data:/app/data" \
  docker/simplereconurl -u https://target.com/ --db /app/data/target.db
```

El registro de comandos y el planificador `--watch` están en `config/system.db` dentro de la imagen. Para preservarlos
entre ejecuciones, monte un archivo del host encima:

```bash
touch config/system.db
docker run --rm \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl -u https://target.com/ --db /app/data/target.db
```

## Claves de API

Las claves **no** quedan incrustadas en la imagen. Monte su `config/api_keys.json` en modo solo lectura
cuando necesite las fuentes autenticadas:

```bash
docker run --rm \
  -v "$PWD/config/api_keys.json:/app/config/api_keys.json:ro" \
  docker/simplereconurl -u https://target.com/ --profile discovery
```

> [!IMPORTANT]
> Monte el archivo en modo solo lectura (`:ro`). Sin él, las fuentes que exigen clave
> simplemente no devuelven nada y la herramienta sigue funcionando.

## Monitoreo continuo (`--watch`)

El planificador es un proceso de primer plano que corre continuamente, así que ejecútelo en segundo plano con la base de sistema persistida:

```bash
# Registrar jobs (escribe en el config/system.db montado)
docker run --rm -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl -u https://target.com/ --profile fast --db /app/data/target.db --quiet \
  --watch-add "0,15,30,45 * * * *"

# Ejecutar el daemon en segundo plano
docker run -d --name recon-watch \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl --watch

docker logs -f recon-watch     # ver cada comando disparado
docker stop recon-watch        # detener el planificador
```

> [!NOTE]
> Los jobs programados corren **dentro** del mismo contenedor, como subprocesos de
> `python simplereconurl.py ...`.
