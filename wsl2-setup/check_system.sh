#!/bin/bash
################################################################################
# 🌙 Moon Dev AI Agents - System Diagnostics
#
# Sprawdza środowisko WSL2, zasoby systemowe, i konfigurację
#
# Użycie: ./wsl2-setup/check_system.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Emoji
CHECK="✅"
CROSS="❌"
WARN="⚠️"
INFO="ℹ️"
ROCKET="🚀"
GEAR="⚙️"

print_header() {
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}🌙 $1${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
    echo "───────────────────────────────────────────────────────────────"
}

print_item() {
    printf "  %-30s : %s\n" "$1" "$2"
}

################################################################################
# System Checks
################################################################################

check_wsl_version() {
    print_section "Wersja WSL"

    if grep -qi microsoft /proc/version; then
        kernel=$(uname -r)

        if grep -qi "WSL2" /proc/version || grep -qi "microsoft-standard" /proc/version; then
            print_item "Status WSL" "${GREEN}${CHECK} WSL2${NC}"
        else
            print_item "Status WSL" "${YELLOW}${WARN} WSL1 (zalecane WSL2)${NC}"
        fi

        print_item "Kernel" "$kernel"

        # Distribution info
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            print_item "Dystrybucja" "$PRETTY_NAME"
            print_item "Wersja" "$VERSION"
        fi
    else
        print_item "Status WSL" "${RED}${CROSS} Nie działa w WSL!${NC}"
        exit 1
    fi
}

check_system_resources() {
    print_section "Zasoby systemowe"

    # CPU
    cpu_model=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
    cpu_cores=$(nproc)
    print_item "CPU Model" "$cpu_model"
    print_item "Liczba rdzeni" "${GREEN}$cpu_cores${NC}"

    # Calculate optimal workers
    optimal_workers=$((cpu_cores - 2))
    if [ "$optimal_workers" -lt 2 ]; then
        optimal_workers=2
    fi
    print_item "Optymalne workery" "${CYAN}$optimal_workers${NC} (dla multi-asset)"

    # RAM
    total_ram=$(free -h | awk '/^Mem:/{print $2}')
    used_ram=$(free -h | awk '/^Mem:/{print $3}')
    free_ram=$(free -h | awk '/^Mem:/{print $4}')

    print_item "RAM Total" "$total_ram"
    print_item "RAM Używane" "$used_ram"
    print_item "RAM Wolne" "${GREEN}$free_ram${NC}"

    # Disk
    disk_total=$(df -h . | tail -1 | awk '{print $2}')
    disk_used=$(df -h . | tail -1 | awk '{print $3}')
    disk_avail=$(df -h . | tail -1 | awk '{print $4}')
    disk_percent=$(df -h . | tail -1 | awk '{print $5}')

    print_item "Dysk Total" "$disk_total"
    print_item "Dysk Używane" "$disk_used ($disk_percent)"
    print_item "Dysk Dostępne" "${GREEN}$disk_avail${NC}"
}

check_conda() {
    print_section "Środowisko Conda"

    if command -v conda &> /dev/null; then
        conda_version=$(conda --version 2>&1)
        print_item "Conda" "${GREEN}${CHECK} Zainstalowane${NC}"
        print_item "Wersja" "$conda_version"
        print_item "Lokalizacja" "$(which conda)"

        # Check if tflow env exists
        if conda env list | grep -q "^tflow "; then
            print_item "Środowisko 'tflow'" "${GREEN}${CHECK} Istnieje${NC}"

            # Get Python version from tflow
            source "$(conda info --base)/etc/profile.d/conda.sh"
            conda activate tflow 2>/dev/null
            if [ $? -eq 0 ]; then
                python_ver=$(python --version 2>&1)
                print_item "Python w tflow" "$python_ver"
            fi
        else
            print_item "Środowisko 'tflow'" "${YELLOW}${WARN} Nie istnieje${NC}"
            echo -e "  ${INFO} Uruchom: ${CYAN}./wsl2-setup/install.sh${NC}"
        fi
    else
        print_item "Conda" "${RED}${CROSS} Nie zainstalowane${NC}"
        echo -e "  ${INFO} Uruchom: ${CYAN}./wsl2-setup/install.sh${NC}"
    fi
}

check_python_packages() {
    print_section "Pakiety Python (w środowisku tflow)"

    # Try to activate tflow
    if command -v conda &> /dev/null && conda env list | grep -q "^tflow "; then
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate tflow 2>/dev/null

        if [ $? -eq 0 ]; then
            # Check critical packages
            packages=("anthropic" "openai" "pandas" "numpy" "backtesting" "pandas_ta" "matplotlib" "seaborn" "openpyxl")

            for package in "${packages[@]}"; do
                if python -c "import $package" 2>/dev/null; then
                    version=$(python -c "import $package; print($package.__version__)" 2>/dev/null || echo "")
                    if [ -n "$version" ]; then
                        print_item "$package" "${GREEN}${CHECK} $version${NC}"
                    else
                        print_item "$package" "${GREEN}${CHECK}${NC}"
                    fi
                else
                    print_item "$package" "${RED}${CROSS} Brak${NC}"
                fi
            done

            # Check optional packages
            echo ""
            echo -e "${CYAN}Pakiety opcjonalne:${NC}"

            if python -c "import talib" 2>/dev/null; then
                print_item "TA-Lib" "${GREEN}${CHECK} Zainstalowane${NC}"
            else
                print_item "TA-Lib" "${YELLOW}${WARN} Brak (użyj pandas_ta)${NC}"
            fi
        else
            echo -e "${YELLOW}${WARN} Nie można aktywować środowiska tflow${NC}"
        fi
    else
        echo -e "${YELLOW}${WARN} Środowisko tflow nie istnieje${NC}"
        echo -e "  ${INFO} Uruchom: ${CYAN}./wsl2-setup/install.sh${NC}"
    fi
}

check_project_structure() {
    print_section "Struktura projektu"

    directories=("src" "src/agents" "src/data" "src/data/ohlcv" "src/data/rbi" "src/models" "src/scripts")

    for dir in "${directories[@]}"; do
        if [ -d "$dir" ]; then
            file_count=$(find "$dir" -maxdepth 1 -type f 2>/dev/null | wc -l)
            print_item "$dir" "${GREEN}${CHECK} ($file_count plików)${NC}"
        else
            print_item "$dir" "${RED}${CROSS} Brak${NC}"
        fi
    done

    # Check critical files
    echo ""
    echo -e "${CYAN}Kluczowe pliki:${NC}"

    files=("requirements.txt" ".env" "src/main.py" "src/config.py" "CLAUDE.md")

    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            size=$(du -h "$file" | cut -f1)
            print_item "$file" "${GREEN}${CHECK} ($size)${NC}"
        else
            print_item "$file" "${YELLOW}${WARN} Brak${NC}"
        fi
    done
}

check_env_configuration() {
    print_section "Konfiguracja .env"

    if [ -f ".env" ]; then
        print_item "Plik .env" "${GREEN}${CHECK} Istnieje${NC}"

        # Check for API keys (without showing values)
        keys=("ANTHROPIC_KEY" "OPENAI_KEY" "DEEPSEEK_KEY" "GROQ_API_KEY" "GEMINI_KEY")

        echo ""
        echo -e "${CYAN}Skonfigurowane klucze API:${NC}"

        any_configured=false
        for key in "${keys[@]}"; do
            if grep -q "^${key}=." .env 2>/dev/null; then
                print_item "$key" "${GREEN}${CHECK} Skonfigurowane${NC}"
                any_configured=true
            else
                print_item "$key" "${YELLOW}${WARN} Brak${NC}"
            fi
        done

        if [ "$any_configured" = false ]; then
            echo ""
            echo -e "  ${YELLOW}${WARN} Brak skonfigurowanych kluczy API!${NC}"
            echo -e "  ${INFO} Edytuj: ${CYAN}nano .env${NC}"
        fi
    else
        print_item "Plik .env" "${RED}${CROSS} Nie istnieje${NC}"
        echo -e "  ${INFO} Uruchom: ${CYAN}./wsl2-setup/install.sh${NC}"
    fi
}

check_git() {
    print_section "Git Repository"

    if command -v git &> /dev/null; then
        print_item "Git" "${GREEN}${CHECK} $(git --version)${NC}"

        if [ -d ".git" ]; then
            print_item "Repozytorium" "${GREEN}${CHECK} Zainicjowane${NC}"

            # Get current branch
            branch=$(git branch --show-current 2>/dev/null)
            if [ -n "$branch" ]; then
                print_item "Bieżąca gałąź" "$branch"
            fi

            # Get remote
            remote=$(git remote get-url origin 2>/dev/null)
            if [ -n "$remote" ]; then
                print_item "Remote" "$remote"
            fi

            # Check for uncommitted changes
            if git diff --quiet && git diff --cached --quiet; then
                print_item "Status" "${GREEN}${CHECK} Czyste (no changes)${NC}"
            else
                print_item "Status" "${YELLOW}${WARN} Uncommitted changes${NC}"
            fi
        else
            print_item "Repozytorium" "${YELLOW}${WARN} Brak .git${NC}"
        fi
    else
        print_item "Git" "${RED}${CROSS} Nie zainstalowane${NC}"
    fi
}

check_internet() {
    print_section "Połączenie sieciowe"

    # Check DNS
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        print_item "Internet (ping)" "${GREEN}${CHECK} Działa${NC}"
    else
        print_item "Internet (ping)" "${RED}${CROSS} Brak odpowiedzi${NC}"
    fi

    # Check specific endpoints
    endpoints=("github.com" "pypi.org" "repo.anaconda.com")

    echo ""
    echo -e "${CYAN}Dostępność endpointów:${NC}"

    for endpoint in "${endpoints[@]}"; do
        if ping -c 1 -W 2 "$endpoint" &> /dev/null; then
            print_item "$endpoint" "${GREEN}${CHECK}${NC}"
        else
            print_item "$endpoint" "${RED}${CROSS}${NC}"
        fi
    done
}

performance_recommendations() {
    print_section "Rekomendacje wydajnościowe"

    cpu_cores=$(nproc)
    optimal_workers=$((cpu_cores - 2))
    if [ "$optimal_workers" -lt 2 ]; then
        optimal_workers=2
    fi

    echo -e "${CYAN}Na podstawie twojego systemu ($cpu_cores rdzeni):${NC}"
    echo ""
    echo -e "  ${GREEN}${ROCKET} Multi-asset testing:${NC}"
    echo -e "    python src/scripts/test_strategy_multi_asset.py strategy.py --workers $optimal_workers"
    echo ""
    echo -e "  ${GREEN}${ROCKET} RBI batch backtest:${NC}"
    echo -e "    python src/agents/rbi_batch_backtester.py --workers $optimal_workers"
    echo ""

    # Check if running on slower storage
    if mount | grep -q "/mnt/c"; then
        echo -e "  ${YELLOW}${WARN} UWAGA: Wykryto ścieżkę /mnt/c${NC}"
        echo -e "    Dla lepszej wydajności, użyj native WSL filesystem (~/):"
        echo -e "    ${CYAN}cd ~ && git clone ...${NC}"
        echo ""
    fi
}

################################################################################
# Main
################################################################################

main() {
    clear
    print_header "MOON DEV AI AGENTS - Diagnostyka systemu"

    # Change to project root if script is in wsl2-setup/
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ "$SCRIPT_DIR" == */wsl2-setup ]]; then
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
    fi

    echo -e "${INFO} Katalog projektu: ${CYAN}$(pwd)${NC}"

    check_wsl_version
    check_system_resources
    check_conda
    check_python_packages
    check_project_structure
    check_env_configuration
    check_git
    check_internet
    performance_recommendations

    echo ""
    print_header "Diagnostyka zakończona"
    echo ""
}

main "$@"
