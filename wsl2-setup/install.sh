#!/bin/bash
################################################################################
# 🌙 Moon Dev AI Agents - WSL2 Auto-Installer
#
# Automatyczna instalacja i konfiguracja środowiska na Windows 11 + WSL2
# Wymaga: WSL2 Ubuntu (dowolna wersja)
#
# Użycie: ./wsl2-setup/install.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emoji support
MOON="🌙"
CHECK="✅"
CROSS="❌"
WARN="⚠️"
ROCKET="🚀"
GEAR="⚙️"
PACKAGE="📦"
KEY="🔑"
FOLDER="📁"
MAGNIFY="🔍"
FIRE="🔥"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${MOON} $1${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}${GEAR} $1${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}${WARN} $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

################################################################################
# System Checks
################################################################################

check_wsl() {
    print_step "Sprawdzanie środowiska WSL2..."

    if grep -qi microsoft /proc/version; then
        print_success "Działa w WSL"

        # Check WSL version
        if grep -qi "WSL2" /proc/version || grep -qi "microsoft-standard" /proc/version; then
            print_success "WSL2 wykryte"
            return 0
        else
            print_warn "Wygląda na WSL1 - zalecane WSL2 dla lepszej wydajności"
            read -p "Kontynuować mimo wszystko? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        print_error "Ten skrypt musi być uruchomiony w WSL!"
        exit 1
    fi
}

check_internet() {
    print_step "Sprawdzanie połączenia z internetem..."

    if ping -c 1 google.com &> /dev/null; then
        print_success "Połączenie z internetem działa"
    else
        print_error "Brak połączenia z internetem!"
        exit 1
    fi
}

check_disk_space() {
    print_step "Sprawdzanie dostępnego miejsca na dysku..."

    available_gb=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')

    if [ "$available_gb" -lt 10 ]; then
        print_error "Za mało miejsca na dysku! Wymagane: 10GB, dostępne: ${available_gb}GB"
        exit 1
    else
        print_success "Dostępne miejsce: ${available_gb}GB"
    fi
}

detect_system_resources() {
    print_step "Wykrywanie zasobów systemowych..."

    cpu_cores=$(nproc)
    total_ram=$(free -g | awk '/^Mem:/{print $2}')

    print_info "CPU: ${cpu_cores} rdzeni"
    print_info "RAM: ${total_ram}GB"

    # Calculate optimal workers (cores - 2, but at least 2)
    optimal_workers=$((cpu_cores - 2))
    if [ "$optimal_workers" -lt 2 ]; then
        optimal_workers=2
    fi

    export OPTIMAL_WORKERS=$optimal_workers
    print_success "Optymalna liczba workerów dla multi-asset: ${optimal_workers}"
}

################################################################################
# Conda Installation
################################################################################

install_miniconda() {
    print_step "Sprawdzanie instalacji Conda..."

    if command -v conda &> /dev/null; then
        print_success "Conda już zainstalowana: $(conda --version)"
        return 0
    fi

    print_warn "Conda nie znaleziona - instaluję Miniconda..."

    cd ~

    # Download Miniconda
    print_step "Pobieranie Miniconda (może zająć kilka minut)..."
    wget -q --show-progress https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

    # Install
    print_step "Instalacja Miniconda..."
    bash miniconda.sh -b -p $HOME/miniconda3
    rm miniconda.sh

    # Initialize
    print_step "Inicjalizacja Conda..."
    ~/miniconda3/bin/conda init bash

    # Source to make conda available
    source ~/.bashrc

    # Verify
    if command -v conda &> /dev/null; then
        print_success "Miniconda zainstalowana pomyślnie: $(conda --version)"
    else
        print_error "Instalacja Miniconda nie powiodła się!"
        exit 1
    fi
}

################################################################################
# Environment Setup
################################################################################

create_conda_env() {
    print_step "Tworzenie środowiska Conda 'tflow'..."

    # Source conda
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    fi

    # Check if env exists
    if conda env list | grep -q "^tflow "; then
        print_warn "Środowisko 'tflow' już istnieje"
        read -p "Usunąć i utworzyć od nowa? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Usuwanie starego środowiska..."
            conda env remove -n tflow -y
        else
            print_info "Używam istniejącego środowiska"
            return 0
        fi
    fi

    print_step "Tworzenie nowego środowiska (Python 3.10)..."
    conda create -n tflow python=3.10 -y -q

    print_success "Środowisko 'tflow' utworzone"
}

install_dependencies() {
    print_step "Instalacja zależności Python (może zająć 5-10 minut)..."

    # Activate environment
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate tflow

    # Upgrade pip
    print_step "Aktualizacja pip..."
    pip install --upgrade pip -q

    # Install from requirements.txt
    if [ -f "requirements.txt" ]; then
        print_step "Instalacja pakietów z requirements.txt..."
        pip install -r requirements.txt -q
        print_success "Zależności zainstalowane z requirements.txt"
    else
        print_warn "Brak requirements.txt - instaluję kluczowe pakiety..."
        pip install anthropic openai pandas numpy backtesting pandas-ta matplotlib seaborn openpyxl python-dotenv termcolor -q
        print_success "Podstawowe pakiety zainstalowane"
    fi

    # Install TA-Lib (optional but recommended)
    print_step "Instalacja TA-Lib (opcjonalne)..."
    if pip install TA-Lib -q 2>/dev/null; then
        print_success "TA-Lib zainstalowany"
    else
        print_warn "TA-Lib nie zainstalowany (wymaga kompilacji) - używaj pandas-ta zamiast tego"
    fi
}

################################################################################
# Configuration
################################################################################

setup_env_file() {
    print_step "Konfiguracja pliku .env..."

    if [ -f ".env" ]; then
        print_warn "Plik .env już istnieje - pomijam"
        return 0
    fi

    if [ -f ".env_example" ]; then
        cp .env_example .env
        print_success "Utworzono .env z szablonu"
        print_warn "PAMIĘTAJ: Musisz dodać swoje klucze API do .env!"
    else
        print_warn "Brak .env_example - tworzę pusty .env"
        touch .env
        cat > .env << 'EOF'
# 🌙 Moon Dev AI Agents - Environment Variables

# AI API Keys (co najmniej jeden wymagany)
ANTHROPIC_KEY=
OPENAI_KEY=
DEEPSEEK_KEY=
GROQ_API_KEY=
GEMINI_KEY=

# Trading APIs (opcjonalne)
BIRDEYE_API_KEY=
MOONDEV_API_KEY=
COINGECKO_API_KEY=

# Blockchain (opcjonalne)
SOLANA_PRIVATE_KEY=
RPC_ENDPOINT=https://api.mainnet-beta.solana.com
EOF
        print_success "Utworzono pusty .env"
    fi
}

create_directory_structure() {
    print_step "Tworzenie struktury katalogów..."

    mkdir -p src/data/ohlcv
    mkdir -p src/data/rbi
    mkdir -p src/data/chat_agent
    mkdir -p src/data/sentiment
    mkdir -p src/data/agent_memory
    mkdir -p src/data/private_data

    print_success "Katalogi utworzone"
}

################################################################################
# Verification
################################################################################

verify_installation() {
    print_step "Weryfikacja instalacji..."

    # Activate environment
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate tflow

    echo ""
    print_info "Sprawdzanie kluczowych pakietów:"

    local all_good=true

    # Check critical packages
    packages=("anthropic" "openai" "pandas" "numpy" "backtesting" "pandas_ta")

    for package in "${packages[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            echo -e "  ${GREEN}${CHECK}${NC} $package"
        else
            echo -e "  ${RED}${CROSS}${NC} $package"
            all_good=false
        fi
    done

    echo ""

    if [ "$all_good" = true ]; then
        print_success "Wszystkie kluczowe pakiety zainstalowane poprawnie!"
        return 0
    else
        print_error "Niektóre pakiety nie zostały zainstalowane poprawnie"
        return 1
    fi
}

################################################################################
# Main Installation Flow
################################################################################

main() {
    print_header "MOON DEV AI AGENTS - AUTO INSTALLER dla WSL2"

    print_info "Ten skrypt automatycznie zainstaluje i skonfiguruje:"
    print_info "  • Miniconda (jeśli brak)"
    print_info "  • Środowisko Python 'tflow'"
    print_info "  • Wszystkie wymagane zależności"
    print_info "  • Strukturę katalogów"
    print_info "  • Plik konfiguracyjny .env"
    echo ""

    read -p "Kontynuować instalację? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Instalacja anulowana"
        exit 0
    fi

    echo ""
    print_header "FAZA 1: Sprawdzanie systemu"
    check_wsl
    check_internet
    check_disk_space
    detect_system_resources

    echo ""
    print_header "FAZA 2: Instalacja Conda"
    install_miniconda

    echo ""
    print_header "FAZA 3: Konfiguracja środowiska"
    create_conda_env
    install_dependencies

    echo ""
    print_header "FAZA 4: Konfiguracja projektu"
    setup_env_file
    create_directory_structure

    echo ""
    print_header "FAZA 5: Weryfikacja"
    if verify_installation; then
        echo ""
        print_header "${FIRE} INSTALACJA ZAKOŃCZONA POMYŚLNIE! ${FIRE}"

        echo ""
        print_info "NASTĘPNE KROKI:"
        echo ""
        echo -e "  ${YELLOW}1.${NC} Edytuj plik .env i dodaj swoje klucze API:"
        echo -e "     ${CYAN}nano .env${NC}"
        echo ""
        echo -e "  ${YELLOW}2.${NC} Aktywuj środowisko:"
        echo -e "     ${CYAN}conda activate tflow${NC}"
        echo ""
        echo -e "  ${YELLOW}3.${NC} Uruchom projekt:"
        echo -e "     ${CYAN}python src/main.py${NC}"
        echo ""
        echo -e "  ${YELLOW}4.${NC} Lub uruchom pojedynczego agenta:"
        echo -e "     ${CYAN}python src/agents/rbi_agent.py${NC}"
        echo ""
        echo -e "  ${YELLOW}5.${NC} Testuj strategie na wielu assetach:"
        echo -e "     ${CYAN}python src/scripts/test_strategy_multi_asset.py strategy.py${NC}"
        echo ""
        print_info "Optymalna liczba workerów dla twojego systemu: ${OPTIMAL_WORKERS}"
        echo ""
        print_success "Miłego kodowania! ${MOON}"
        echo ""

        # Add conda activation to bashrc if not already there
        if ! grep -q "conda activate tflow" ~/.bashrc; then
            echo ""
            read -p "Dodać 'conda activate tflow' do ~/.bashrc? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "" >> ~/.bashrc
                echo "# Moon Dev - auto activate tflow environment" >> ~/.bashrc
                echo "conda activate tflow" >> ~/.bashrc
                print_success "Dodano autoaktywację do ~/.bashrc"
            fi
        fi
    else
        echo ""
        print_error "Instalacja zakończona z błędami"
        print_info "Sprawdź logi powyżej i spróbuj ponownie"
        exit 1
    fi
}

################################################################################
# Run
################################################################################

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

main "$@"
