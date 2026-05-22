#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

echo "======================================="
echo "PEKA Bootstrap Starting"
echo "Project root: ${PROJECT_ROOT}"
echo "======================================="

cd "${PROJECT_ROOT}"

echo "[1/7] OS validation"

if [[ ! -f /etc/os-release ]]; then
  echo "ERROR: Cannot detect Linux OS."
  exit 1
fi

source /etc/os-release
echo "Detected OS: ${PRETTY_NAME}"

case "${ID}" in
  ubuntu|debian)
    PKG_MANAGER="apt"
    ;;
  rhel|rocky|almalinux|centos|fedora)
    PKG_MANAGER="dnf"
    ;;
  *)
    echo "WARNING: Unsupported OS '${ID}'. Bootstrap may fail."
    PKG_MANAGER="unknown"
    ;;
esac

CPU_COUNT="$(nproc)"
MEM_GB="$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)"
DISK_FREE_GB="$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {gsub("G","",$4); print $4}')"

echo "CPU cores: ${CPU_COUNT}"
echo "Memory GB: ${MEM_GB}"
echo "Free disk GB: ${DISK_FREE_GB}"

if (( MEM_GB < 8 )); then
  echo "WARNING: Less than 8 GB RAM detected. PEKA may run slowly."
fi

if (( DISK_FREE_GB < 20 )); then
  echo "WARNING: Less than 20 GB free disk detected."
fi

echo "[2/7] Installing prerequisites"

install_apt() {
  sudo apt update
  sudo apt install -y \
    curl \
    wget \
    git \
    jq \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    python3-venv

  if ! command -v docker >/dev/null 2>&1; then
    echo "Installing Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
      sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt update
    sudo apt install -y \
      docker-ce \
      docker-ce-cli \
      containerd.io \
      docker-buildx-plugin \
      docker-compose-plugin
  fi
}

install_dnf() {
  sudo dnf install -y \
    curl \
    wget \
    git \
    jq \
    unzip \
    ca-certificates \
    python3 \
    python3-pip

  if ! command -v docker >/dev/null 2>&1; then
    echo "Installing Docker..."
    sudo dnf install -y dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install -y \
      docker-ce \
      docker-ce-cli \
      containerd.io \
      docker-buildx-plugin \
      docker-compose-plugin
  fi
}

case "${PKG_MANAGER}" in
  apt)
    install_apt
    ;;
  dnf)
    install_dnf
    ;;
  *)
    echo "ERROR: Cannot install prerequisites automatically for this OS."
    exit 1
    ;;
esac

sudo systemctl enable docker
sudo systemctl start docker

if ! groups "$USER" | grep -q docker; then
  echo "Adding ${USER} to docker group..."
  sudo usermod -aG docker "$USER"
  echo "WARNING: You may need to log out and back in for docker group permissions."
fi

echo "[3/7] Creating .env and directories"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo ".env already exists"
fi

set -a
source "${ENV_FILE}"
set +a

PEKA_DATA_DIR="${PEKA_DATA_DIR:-/opt/peka/data}"

mkdir -p \
  "${PEKA_DATA_DIR}/qdrant" \
  "${PEKA_DATA_DIR}/ollama" \
  "${PEKA_DATA_DIR}/openwebui" \
  "${PEKA_DATA_DIR}/wiki" \
  "${PEKA_DATA_DIR}/cmdb" \
  "${PEKA_DATA_DIR}/rvtools" \
  "${PEKA_DATA_DIR}/logs" \
  "${PROJECT_ROOT}/logs"

echo "Data directory: ${PEKA_DATA_DIR}"

echo "[4/7] Creating Python virtual environment"

if [[ ! -d "${PROJECT_ROOT}/venv" ]]; then
  python3 -m venv "${PROJECT_ROOT}/venv"
fi

source "${PROJECT_ROOT}/venv/bin/activate"

echo "[5/7] Installing Python requirements"

python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[6/7] Starting Docker services"

docker compose --env-file .env -f docker/docker-compose.yml up -d

echo "[7/7] Validating services"

check_service() {
  local name="$1"
  local url="$2"
  local max_attempts=30
  local attempt=1

  echo "Checking ${name}..."

  while (( attempt <= max_attempts )); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "${name} OK"
      return 0
    fi

    echo "${name} not ready yet... attempt ${attempt}/${max_attempts}"
    sleep 3
    ((attempt++))
  done

  echo "${name} FAILED"
  return 1
}

check_service "Qdrant" "http://localhost:6333/collections" || true
check_service "Ollama" "http://localhost:11434/api/tags" || true
check_service "Open WebUI" "http://localhost:3000" || true

echo "======================================="
echo "PEKA Bootstrap Complete"
echo "======================================="
echo "Next steps:"
echo "1. Place wiki files under: ${PEKA_DATA_DIR}/wiki"
echo "2. Pull model: ./scripts/pull-model.sh"
echo "3. Rebuild index: ./scripts/rebuild-index.sh"
echo "4. Start API: ./scripts/start-api.sh"
echo "5. Open UI: http://<server-ip>:8000/ui"
echo "======================================="