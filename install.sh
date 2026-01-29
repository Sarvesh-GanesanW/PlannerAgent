#!/usr/bin/env bash

set -e

REPO_URL="https://github.com/Sarvesh-GanesanW/PlannerAgent"
INSTALL_DIR="${HOME}/.local/bin"
BINARY_NAME="plan-agent"
INSTALL_PATH="${HOME}/.local/share/plan-agent"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SPINNER_PID=""

error() {
    stop_spinner
    echo -e "${RED}❌ $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

step() {
    echo -e "${BLUE}→ $1${NC}"
}

start_spinner() {
    local message="$1"
    local spinner_chars="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    local delay=0.08

    printf "${CYAN}%s${NC} " "$message"

    while true; do
        for (( i=0; i<${#spinner_chars}; i++ )); do
            printf "\r${CYAN}%s %s${NC}" "$message" "${spinner_chars:$i:1}"
            sleep $delay
        done
    done &

    SPINNER_PID=$!
}

start_slider() {
    local message="$1"
    local width=20
    local delay=0.1

    printf "${CYAN}%s${NC} " "$message"

    while true; do
        for (( pos=0; pos<width; pos++ )); do
            local bar=""
            for (( i=0; i<width; i++ )); do
                if [ $i -eq $pos ]; then
                    bar="${bar}█"
                elif [ $i -eq $((pos-1)) ] || [ $i -eq $((pos+1)) ]; then
                    bar="${bar}░"
                else
                    bar="${bar}·"
                fi
            done
            printf "\r${CYAN}%s [%s]${NC}" "$message" "$bar"
            sleep $delay
        done
    done &

    SPINNER_PID=$!
}

start_dots() {
    local message="$1"
    local max_dots=3
    local delay=0.4

    printf "${CYAN}%s${NC}" "$message"

    local count=0
    while true; do
        local dots=""
        for (( i=0; i<count; i++ )); do
            dots="${dots}."
        done
        printf "\r${CYAN}%s%s${NC}   " "$message" "$dots"
        count=$(( (count + 1) % (max_dots + 1) ))
        sleep $delay
    done &

    SPINNER_PID=$!
}

stop_spinner() {
    if [ -n "$SPINNER_PID" ]; then
        kill "$SPINNER_PID" 2>/dev/null || true
        wait "$SPINNER_PID" 2>/dev/null || true
        printf "\r"
    fi
    SPINNER_PID=""
}

find_python() {
    local python_cmd=""

    for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
        if command -v "$cmd" &> /dev/null; then
            python_cmd=$(command -v "$cmd" 2>/dev/null | head -n1)
            version=$($python_cmd --version 2>&1 | head -n1 | awk '{print $2}')
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)

            if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ]; then
                printf '%s' "$python_cmd"
                return 0
            fi
        fi
    done

    if [ -n "$CONDA_DEFAULT_ENV" ] && [ -n "$CONDA_PYTHON_EXE" ]; then
        printf '%s' "$CONDA_PYTHON_EXE"
        return 0
    fi

    for path in "$HOME/anaconda3/bin/python3" "$HOME/miniconda3/bin/python3"; do
        if [ -f "$path" ]; then
            printf '%s' "$path"
            return 0
        fi
    done

    return 1
}

install_uv() {
    start_slider "Installing uv (fast Python package manager)"

    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    else
        stop_spinner
        error "Neither curl nor wget found. Please install one of them."
    fi

    stop_spinner

    if [ -f "$HOME/.local/bin/env" ]; then
        . "$HOME/.local/bin/env"
    fi
}

echo "🤖 Installing Plan Agent..."
echo ""

if ! command -v uv &> /dev/null; then
    warn "uv not found. Installing uv for faster package management..."
    install_uv
fi

if ! command -v uv &> /dev/null; then
    if [ -f "$HOME/.cargo/bin/uv" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    elif [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    else
        error "Failed to install uv. Please install it manually: https://github.com/astral-sh/uv"
    fi
fi

info "Using uv: $(uv --version)"

PYTHON_CMD=$(find_python)
PYTHON_CMD=$(echo "$PYTHON_CMD" | head -n1 | tr -d '\n\r' | xargs)

if [ -z "$PYTHON_CMD" ]; then
    error "Python 3.9+ is required. Please install Python 3.9+ first."
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | head -n1 | awk '{print $2}')
info "Found Python $PYTHON_VERSION at $PYTHON_CMD"

mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_PATH"

start_spinner "Downloading Plan Agent"
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

curl -fsSL "$REPO_URL/archive/refs/heads/main.tar.gz" -o plan-agent.tar.gz 2>/dev/null || {
    stop_spinner
    error "Failed to download"
}

tar -xzf plan-agent.tar.gz 2>/dev/null || {
    stop_spinner
    error "Failed to extract"
}

cd PlannerAgent-main
stop_spinner
info "Downloaded and extracted"

start_dots "Creating virtual environment"
uv venv "$INSTALL_PATH/.venv" --python "$PYTHON_CMD" 2>&1 > /dev/null || {
    stop_spinner
    error "Failed to create virtual environment with Python: $PYTHON_CMD"
}
stop_spinner
info "Virtual environment created"

start_slider "Installing dependencies (this is fast with uv)"
UV_PYTHON="$INSTALL_PATH/.venv/bin/python"
uv pip install -q --python "$UV_PYTHON" -r requirements.txt > /dev/null 2>&1 || {
    stop_spinner
    error "Failed to install dependencies"
}
stop_spinner
info "Dependencies installed"

cp -r . "$INSTALL_PATH/"

cat > "$INSTALL_DIR/$BINARY_NAME" << 'LAUNCHER'
#!/bin/bash
INSTALL_PATH="${HOME}/.local/share/plan-agent"

if [ ! -d "$INSTALL_PATH" ]; then
    echo "Error: Plan Agent not found at $INSTALL_PATH"
    exit 1
fi

export PATH="$INSTALL_PATH/.venv/bin:$PATH"

if [ "$1" == "config" ]; then
    exec "$INSTALL_PATH/.venv/bin/python" "$INSTALL_PATH/main.py" config
elif [ "$1" == "artifacts" ]; then
    exec "$INSTALL_PATH/.venv/bin/python" "$INSTALL_PATH/main.py" artifacts
else
    exec "$INSTALL_PATH/.venv/bin/python" "$INSTALL_PATH/main.py" "$@"
fi
LAUNCHER

chmod +x "$INSTALL_DIR/$BINARY_NAME"

cat > "$INSTALL_DIR/plan-agent-uninstall" << 'UNINSTALLER'
#!/bin/bash
INSTALL_PATH="${HOME}/.local/share/plan-agent"
INSTALL_DIR="${HOME}/.local/bin"

echo "🗑️  Uninstalling Plan Agent..."

if [ -d "$INSTALL_PATH" ]; then
    rm -rf "$INSTALL_PATH"
    echo "✓ Removed $INSTALL_PATH"
fi

if [ -f "$INSTALL_DIR/plan-agent" ]; then
    rm -f "$INSTALL_DIR/plan-agent"
    echo "✓ Removed plan-agent"
fi

if [ -f "$INSTALL_DIR/plan-agent-uninstall" ]; then
    rm -f "$INSTALL_DIR/plan-agent-uninstall"
    echo "✓ Removed uninstaller"
fi

echo ""
echo "✓ Plan Agent uninstalled successfully!"
echo ""
echo "Note: If you added PATH exports to your shell profile, you may want to remove them."
UNINSTALLER

chmod +x "$INSTALL_DIR/plan-agent-uninstall"

cd /
rm -rf "$TMP_DIR"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    warn "Please add the following to your shell profile (~/.bashrc, ~/.zshrc, or ~/.config/fish/config.fish):"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run: source ~/.bashrc (or restart your terminal)"
fi

echo ""
info "Plan Agent installed successfully!"
echo ""
echo "🚀 Quick start:"
echo ""
echo "   plan-agent config    # Configure your API key"
echo "   plan-agent           # Start the agent"
echo ""
echo "🗑️  To uninstall:"
echo ""
echo "   plan-agent-uninstall"
echo ""
