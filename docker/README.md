# Docker

<p align="center">
<a href="README.md"><img alt="Português" src="https://img.shields.io/badge/%F0%9F%87%A7%F0%9F%87%B7_Portugu%C3%AAs-1E88E5?style=for-the-badge"></a>
<a href="README_EN.md"><img alt="English" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-757575?style=for-the-badge"></a>
<a href="README_ES.md"><img alt="Español" src="https://img.shields.io/badge/%F0%9F%87%AA%F0%9F%87%B8_Espa%C3%B1ol-757575?style=for-the-badge"></a>
</p>

Roda o SimpleReconURL em contêiner, sem precisar de Python instalado na máquina.

## Build

São dois caminhos de build, e ambos produzem a mesma imagem `docker/simplereconurl`.

### Opção A: a partir do código local (`docker/Dockerfile`)

Faça o build a partir da **raiz do repositório** (o contexto precisa incluir o projeto inteiro):

```bash
docker build -t docker/simplereconurl -f docker/Dockerfile .
```

### Opção B: direto do GitHub (`docker/Dockerfile.remote`)

Não precisa de checkout local. Este Dockerfile clona o projeto sozinho, então o contexto de build é ignorado:

```bash
# com um contexto descartável
docker build -t docker/simplereconurl -f docker/Dockerfile.remote .

# sem contexto nenhum (mandando o Dockerfile pelo pipe)
docker build -t docker/simplereconurl - < docker/Dockerfile.remote

# sem nada clonado, buildando a partir da URL crua
curl -sSL https://raw.githubusercontent.com/osintbrazuca/SimpleReconURL/master/docker/Dockerfile.remote \
  | docker build -t docker/simplereconurl -
```

Para fixar um branch, tag ou fork, use build args:

```bash
docker build -t docker/simplereconurl -f docker/Dockerfile.remote \
  --build-arg REF=v1.0.0 \
  --build-arg REPO_URL=https://github.com/osintbrazuca/SimpleReconURL.git .
```

## Execução

Tudo que vier depois do nome da imagem é repassado direto para o `python simplereconurl.py`:

```bash
# O exemplo principal
docker run --rm docker/simplereconurl -u https://target.com/

# Sem argumentos -> ajuda
docker run --rm docker/simplereconurl

# Listar fontes / perfis / exemplos
docker run --rm docker/simplereconurl --list-sources
docker run --rm docker/simplereconurl --list-profiles

# Pronto para pipe (saída fora de TTY sai sem cor automaticamente)
docker run --rm docker/simplereconurl -u https://target.com/ --no-banner | httpx -silent

# Saída interativa e colorida
docker run --rm -it docker/simplereconurl -u https://target.com/ --profile crawl
```

## Persistindo dados (resultados, log de comandos, jobs do watch)

> [!WARNING]
> Com `--rm` o contêiner é efêmero e tudo que ele gravou é descartado ao terminar.
> Monte um diretório do host e aponte o `--db` para ele para manter os resultados.

```bash
mkdir -p data
docker run --rm -v "$PWD/data:/app/data" \
  docker/simplereconurl -u https://target.com/ --db /app/data/target.db
```

O log de comandos e o agendador `--watch` ficam em `config/system.db` dentro da imagem. Para preservá-los
entre execuções, monte um arquivo do host por cima:

```bash
touch config/system.db
docker run --rm \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl -u https://target.com/ --db /app/data/target.db
```

## Chaves de API

As chaves **não** ficam embutidas na imagem. Monte seu `config/api_keys.json` em modo somente leitura
quando precisar das fontes autenticadas:

```bash
docker run --rm \
  -v "$PWD/config/api_keys.json:/app/config/api_keys.json:ro" \
  docker/simplereconurl -u https://target.com/ --profile discovery
```

> [!IMPORTANT]
> Monte o arquivo em modo somente leitura (`:ro`). Sem ele, as fontes que exigem chave
> simplesmente não retornam nada e a ferramenta continua funcionando.

## Monitoramento contínuo (`--watch`)

O agendador é um processo de primeiro plano que roda continuamente, então execute-o em segundo plano com o banco de sistema persistido:

```bash
# Registrar jobs (grava no config/system.db montado)
docker run --rm -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl -u https://target.com/ --profile fast --db /app/data/target.db --quiet \
  --watch-add "0,15,30,45 * * * *"

# Rodar o daemon em segundo plano
docker run -d --name recon-watch \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl --watch

docker logs -f recon-watch     # ver cada comando disparado
docker stop recon-watch        # parar o agendador
```

> [!NOTE]
> Os jobs agendados rodam **dentro** do mesmo contêiner, como subprocessos do
> `python simplereconurl.py ...`.
