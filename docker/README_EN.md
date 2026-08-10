# Docker

<p align="center">
<a href="README.md"><img alt="Português" src="https://img.shields.io/badge/%F0%9F%87%A7%F0%9F%87%B7_Portugu%C3%AAs-757575?style=for-the-badge"></a>
<a href="README_EN.md"><img alt="English" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-1E88E5?style=for-the-badge"></a>
<a href="README_ES.md"><img alt="Español" src="https://img.shields.io/badge/%F0%9F%87%AA%F0%9F%87%B8_Espa%C3%B1ol-757575?style=for-the-badge"></a>
</p>

Run SimpleReconURL in a container, no local Python setup required.

## Build

There are two build paths, both producing the same `docker/simplereconurl` image.

### Option A: from local code (`docker/Dockerfile`)

Build from the **repository root** (the build context must include the whole project):

```bash
docker build -t docker/simplereconurl -f docker/Dockerfile .
```

### Option B: straight from GitHub (`docker/Dockerfile.remote`)

No local checkout needed. This Dockerfile clones the project itself, so the build context is ignored:

```bash
# with a throwaway context
docker build -t docker/simplereconurl -f docker/Dockerfile.remote .

# fully context-less (pipe the Dockerfile in)
docker build -t docker/simplereconurl - < docker/Dockerfile.remote

# nothing checked out at all, build from the raw URL
curl -sSL https://raw.githubusercontent.com/osintbrazuca/SimpleReconURL/master/docker/Dockerfile.remote \
  | docker build -t docker/simplereconurl -
```

Pin a branch/tag or a fork with build args:

```bash
docker build -t docker/simplereconurl -f docker/Dockerfile.remote \
  --build-arg REF=v1.0.0 \
  --build-arg REPO_URL=https://github.com/osintbrazuca/SimpleReconURL.git .
```

## Run

Any arguments after the image name are passed straight to `python simplereconurl.py`:

```bash
# The headline example
docker run --rm docker/simplereconurl -u https://target.com/

# No arguments -> help
docker run --rm docker/simplereconurl

# List sources / profiles / examples
docker run --rm docker/simplereconurl --list-sources
docker run --rm docker/simplereconurl --list-profiles

# Pipe-friendly (non-TTY output is automatically uncolored)
docker run --rm docker/simplereconurl -u https://target.com/ --no-banner | httpx -silent

# Interactive / colored output
docker run --rm -it docker/simplereconurl -u https://target.com/ --profile crawl
```

## Persisting data (results, command log, watch jobs)

> [!WARNING]
> With `--rm` the container is ephemeral and anything it wrote is discarded on exit.
> Mount a host directory and point `--db` at it to keep results.

```bash
mkdir -p data
docker run --rm -v "$PWD/data:/app/data" \
  docker/simplereconurl -u https://target.com/ --db /app/data/target.db
```

The command log and the `--watch` scheduler live in `config/system.db` inside the image. To persist them
across runs, mount a host file over it:

```bash
touch config/system.db
docker run --rm \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl -u https://target.com/ --db /app/data/target.db
```

## API keys

Keys are **not** baked into the image. Mount your `config/api_keys.json` read-only when you need
authenticated sources:

```bash
docker run --rm \
  -v "$PWD/config/api_keys.json:/app/config/api_keys.json:ro" \
  docker/simplereconurl -u https://target.com/ --profile discovery
```

> [!IMPORTANT]
> Mount the file read-only (`:ro`). Without it, key-required sources simply return
> nothing and the tool still runs.

## Continuous monitoring (`--watch`)

The scheduler is a long-running foreground process, so run it detached with the system DB persisted:

```bash
# Register jobs (writes to the mounted config/system.db)
docker run --rm -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl -u https://target.com/ --profile fast --db /app/data/target.db --quiet \
  --watch-add "0,15,30,45 * * * *"

# Run the daemon detached
docker run -d --name recon-watch \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config/system.db:/app/config/system.db" \
  docker/simplereconurl --watch

docker logs -f recon-watch     # see each fired command
docker stop recon-watch        # stop the scheduler
```

> [!NOTE]
> Scheduled jobs run **inside** the same container, as `python simplereconurl.py ...`
> subprocesses.
