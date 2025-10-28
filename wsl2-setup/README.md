# 🌙 Moon Dev AI Agents - Instalacja WSL2

Szybka i automatyczna instalacja Moon Dev AI Agents na Windows 11 + WSL2.

## 📋 Wymagania

- **Windows 11** z zainstalowanym **WSL2 Ubuntu** (dowolna wersja)
- Co najmniej **10GB wolnego miejsca**
- Połączenie z internetem

Jeśli nie masz jeszcze WSL2, otwórz PowerShell jako Administrator i uruchom:
```powershell
wsl --install -d Ubuntu-22.04
```

## 🚀 Instalacja (4 kroki)

### Krok 1: Otwórz terminal WSL2 Ubuntu

W Windows Terminal wybierz Ubuntu lub wpisz `wsl` w PowerShell.

### Krok 2: Sklonuj repozytorium

```bash
cd ~
git clone https://github.com/andrewbitlab/moon-dev-ai-agents.git
cd moon-dev-ai-agents
```

**Uwaga:** Jeśli nie masz skonfigurowanego SSH z GitHubem, użyj HTTPS:
```bash
git clone https://github.com/andrewbitlab/moon-dev-ai-agents.git
```

### Krok 3: Uruchom autoinstalator

```bash
chmod +x wsl2-setup/install.sh
./wsl2-setup/install.sh
```

Skrypt automatycznie:
- ✅ Sprawdzi środowisko WSL2
- ✅ Zainstaluje Miniconda (jeśli brak)
- ✅ Utworzy środowisko Python `tflow`
- ✅ Zainstaluje wszystkie zależności (~5-10 min)
- ✅ Skonfiguruje strukturę katalogów
- ✅ Utworzy plik `.env` z szablonu

**Po instalacji zobaczysz:**
```
═══════════════════════════════════════════════════════════════
🌙 🔥 INSTALACJA ZAKOŃCZONA POMYŚLNIE! 🔥
═══════════════════════════════════════════════════════════════
```

### Krok 4: Skonfiguruj klucze API

Edytuj plik `.env` i dodaj swoje klucze:

```bash
nano .env
```

**Minimalna konfiguracja (wybierz co najmniej jeden):**
```bash
# AI API Keys
ANTHROPIC_KEY=sk-ant-xxx...
OPENAI_KEY=sk-xxx...
```

Zapisz: `Ctrl+O`, `Enter`, `Ctrl+X`

## ✨ Gotowe! Uruchom projekt

```bash
# Aktywuj środowisko (jeśli jeszcze nie aktywne)
conda activate tflow

# Uruchom główny orchestrator (wszystkie agenty)
python src/main.py

# LUB uruchom pojedynczego agenta
python src/agents/rbi_agent.py
python src/agents/chat_agent.py
```

---

## 🛠️ Komendy użytkowe

### Znajdź wszystkie strategie w projekcie
```bash
python src/scripts/find_strategies.py
```

### Testuj strategię na wielu assetach (BTC, ETH, SOL, etc.)
```bash
python src/scripts/test_strategy_multi_asset.py src/data/rbi/03_14_2025/backtests_final/MomentumStrategy_BTFinal.py
```

### Analizuj wyniki backtestów
```bash
python src/scripts/analyze_rbi_results.py results.json --excel report.xlsx --plots
```

### Sprawdź status systemu
```bash
./wsl2-setup/check_system.sh
```

---

## 🔧 Optymalizacja dla 5950X + 64GB RAM

Twój system ma **32 rdzenie** - autoinstalator automatycznie wykryje i ustawi optymalną liczbę workerów (~30).

**Multi-asset testing z maksymalną wydajnością:**
```bash
# Auto-wykrywa liczbę rdzeni
python src/scripts/test_strategy_multi_asset.py strategy.py

# Niestandardowa liczba workerów
python src/scripts/test_strategy_multi_asset.py strategy.py --workers 24

# Zwiększ timeout dla złożonych strategii
python src/scripts/test_strategy_multi_asset.py strategy.py --timeout 600
```

**Batch backtest:**
```bash
python src/agents/rbi_batch_backtester.py --workers 20
```

---

## 🐛 Troubleshooting

### Problem: Brak komendy `conda`
```bash
source ~/miniconda3/bin/activate
conda init bash
source ~/.bashrc
```

### Problem: `ModuleNotFoundError`
```bash
conda activate tflow
pip install -r requirements.txt
```

### Problem: Wolne działanie
- Sprawdź czy używasz WSL2 (nie WSL1): `wsl -l -v` w PowerShell
- Upewnij się że projekt jest w filesystem WSL (~/ nie /mnt/c/)
- Zwiększ RAM dla WSL w `.wslconfig`:

```ini
# %USERPROFILE%\.wslconfig
[wsl2]
memory=32GB
processors=16
```

### Problem: `TA-Lib` nie instaluje się
To opcjonalne - użyj `pandas_ta` zamiast `talib`:
```python
import pandas_ta as ta
df.ta.rsi()  # zamiast talib.RSI()
```

### Problem: Błędy CUDA/GPU
WSL2 wspiera CUDA jeśli masz NVIDIA GPU. Jeśli nie używasz GPU, ignoruj te błędy - wszystko działa na CPU.

---

## 📊 Sprawdzanie systemu

### Diagnostyka zasobów
```bash
./wsl2-setup/check_system.sh
```

### Wykrywanie liczby rdzeni
```bash
nproc
# Output: 32 (dla 5950X)
```

### Sprawdzanie RAM
```bash
free -h
```

### Sprawdzanie wersji pakietów
```bash
conda activate tflow
pip list | grep -E "anthropic|openai|backtesting|pandas"
```

---

## 🔄 Aktualizacja projektu

```bash
cd ~/moon-dev-ai-agents
git pull origin main

# Jeśli dodano nowe pakiety:
conda activate tflow
pip install -r requirements.txt
```

---

## 📁 Struktura projektu

```
moon-dev-ai-agents/
├── src/
│   ├── agents/              # 48+ AI agents
│   │   ├── rbi_agent.py     # Research-Based Inference
│   │   ├── rbi_multi_asset_tester.py  # Multi-asset backtesting
│   │   └── ...
│   ├── scripts/             # Narzędzia CLI
│   │   ├── find_strategies.py         # Odkryj 1,377+ strategii
│   │   ├── test_strategy_multi_asset.py  # Test na wielu assetach
│   │   └── analyze_rbi_results.py     # Analiza wyników
│   ├── data/
│   │   ├── ohlcv/           # Dane OHLCV (BTC, ETH, SOL...)
│   │   └── rbi/             # Wygenerowane strategie
│   ├── models/              # LLM abstraction (ModelFactory)
│   └── config.py            # Konfiguracja główna
├── wsl2-setup/              # Skrypty instalacyjne WSL2
├── .env                     # Twoje klucze API (nie commituj!)
└── CLAUDE.md                # Dokumentacja dla AI
```

---

## 🌟 Szybki start z backtesting

### 1. Wygeneruj strategię z YouTube
```bash
python src/agents/rbi_agent.py
# Podaj URL do video z strategią tradingową
```

### 2. Testuj wygenerowaną strategię na wielu assetach
```bash
python src/scripts/test_strategy_multi_asset.py src/data/rbi/latest_strategy_BT.py
```

### 3. Analizuj wyniki
```bash
# Pokaże ranking assetów według Sharpe Ratio
# Eksportuje do JSON
```

---

## 💡 Wskazówki

1. **Zawsze aktywuj środowisko `tflow` przed uruchomieniem skryptów**
   ```bash
   conda activate tflow
   ```

2. **Projekt działa najlepiej w native WSL filesystem (~/) nie w /mnt/c/**
   - Lepszy I/O performance
   - Unikaj ścieżek Windows (C:\...)

3. **Używaj VSCode z WSL extension** dla najlepszego developer experience
   ```bash
   code .
   ```

4. **Git konfiguracja w WSL** (jeśli jeszcze nie zrobione)
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your@email.com"
   ```

---

## 📚 Więcej informacji

- **Dokumentacja główna:** [CLAUDE.md](../CLAUDE.md)
- **Model Factory:** [src/models/README.md](../src/models/README.md)
- **GitHub Issues:** https://github.com/andrewbitlab/moon-dev-ai-agents/issues

---

## ❓ Najczęściej zadawane pytania

**Q: Czy mogę użyć różnych modeli AI?**
A: Tak! Projekt wspiera Claude, GPT-4, DeepSeek, Groq, Gemini, Ollama. Skonfiguruj w `src/config.py` lub użyj ModelFactory.

**Q: Czy potrzebuję GPU?**
A: Nie. Wszystko działa na CPU. GPU jest opcjonalne dla CUDA-accelerated backtesting.

**Q: Ile zajmuje miejsca?**
A: ~5GB dla środowiska + dependencies, dodatkowe ~1-2GB dla danych OHLCV jeśli je pobierzesz.

**Q: Czy to działa na WSL1?**
A: Technicznie tak, ale WSL2 jest zdecydowanie szybsze. Upgrade: `wsl --set-version Ubuntu-22.04 2`

**Q: Jak zaktualizować Python w środowisku?**
A:
```bash
conda create -n tflow python=3.11 -y
conda activate tflow
pip install -r requirements.txt
```

---

**🌙 Happy Trading! Built with ❤️ by Moon Dev community**
