# C2D2 Blockchain Monitor

Aplikacja monitorująca sieć testową Sepolia (Ethereum) w czasie rzeczywistym.  
Pobiera dane bloków i transakcji, filtruje je i prezentuje wyniki w graficznym interfejsie użytkownika (GUI) oraz zapisuje do plików CSV i tekstowych raportów podsumowujących.

---

## Spis treści

1. [Dokumentacja Funkcjonalna](#1-dokumentacja-funkcjonalna)
2. [Dokumentacja Niefunkcjonalna](#2-dokumentacja-niefunkcjonalna)
3. [Instalacja i uruchomienie](#3-instalacja-i-uruchomienie)
4. [Podział zadań i harmonogram](#4-podział-zadań-i-harmonogram)

---

## 1. Dokumentacja Funkcjonalna

### 1.1 Funkcjonalności MVP (Must-Have)

| Funkcjonalność | Opis |
|---|---|
| **Pobieranie bloków** | Aplikacja pobiera dane dla co najmniej **100 najnowszych bloków** sieci Sepolia: numer bloku, hash bloku, liczba transakcji. |
| **Pobieranie transakcji** | Dla **10 najnowszych bloków** pobierane są szczegóły ostatniej transakcji: hash TX, adres nadawcy, adres odbiorcy, wartość ETH, zużycie gasu, cena gasu, opłata. |
| **Monitorowanie na żywo** | Po załadowaniu bloków historycznych aplikacja subskrybuje nowe bloki przez WebSocket (`eth_subscribe newHeads`) i przetwarza je w czasie rzeczywistym. |
| **Filtrowanie transakcji** | Użytkownik może wybrać filtr (np. minimalna cena gazu, minimalna wartość ETH, transakcje zakończone błędem, interakcje z kontraktami) przed uruchomieniem monitorowania. |
| **Raportowanie konsolowe** | Każdy przetworzony blok i transakcja są logowane na bieżąco do konsoli i pliku `.log`. |
| **Raport podsumowujący** | Po zakończeniu sesji generowany jest plik `.txt` z kluczowymi statystykami (liczba bloków, transakcji, łączne ETH, gaz, czas sesji). |
| **Eksport CSV** | Wszystkie transakcje przechodzące przez filtry zapisywane są do pliku `.csv` w katalogu `logs/csv/`. |

### 1.2 Funkcjonalności rozszerzone (Nice-to-Have – zaimplementowane)

- **Zakładka Analytics** – agregowane metryki w czasie rzeczywistym (średni czas bloku, średnie ETH/TX, unikalni nadawcy/odbiorcy, pula opłat).
- **Wyszukiwanie** w tabelach bloków i transakcji po numerze bloku lub hashu.
- **Tryb ciągłego nasłuchiwania** (`Listen endlessly`) – aplikacja pracuje do momentu kliknięcia Stop.
- **Konfigurowalny zakres** – użytkownik wybiera liczbę bloków historycznych (0–100) oraz liczbę bloków na żywo do odebrania.

### 1.3 Opis warstw architektonicznych

#### Warstwa Dostępu (`access_layer.py`)

Odpowiada za całą komunikację z siecią Ethereum. Nie zawiera logiki biznesowej.

- `is_connected()` – weryfikuje połączenie HTTP z węzłem Sepolia.
- `get_latest_block_number()` – zwraca numer najnowszego bloku.
- `get_block(block_num, full_transactions)` – pobiera blok wraz z pełnymi danymi transakcji.
- `get_transaction_receipt(tx_hash)` – pobiera potwierdzenie transakcji (zawiera `gasUsed`, `status`).
- `from_wei(value, unit)` – przelicza Wei na ETH/Gwei.
- `subscribe_new_heads(callback)` – otwiera stałe połączenie WebSocket i subskrybuje `newHeads`; wywołuje `callback(block_num)` dla każdego nowego bloku. Automatycznie wznawia połączenie po jego zerwaniu.

#### Warstwa Logiki Biznesowej (`business_logic_layer.py`)

Przetwarza surowe dane z warstwy dostępu, oblicza statystyki, stosuje filtry.

- `process_block_data(block)` – wyciąga kluczowe pola, inkrementuje liczniki, zwraca ustandaryzowany słownik.
- `process_transaction_data(tx_details, tx_receipt)` – oblicza opłatę, aktualizuje statystyki, stosuje filtry, zwraca słownik lub `None` gdy TX odfiltrowany.
- `passes_filters(tx_details, tx_receipt)` – sprawdza wszystkie aktywne filtry (wzorzec strategii).
- `get_aggregated_stats()` – zwraca końcowe statystyki sesji.
- `get_live_analytics()` – zwraca bieżące metryki agregowane (średni czas bloku, opłaty, unikalne adresy).
- `fetch_latest_blocks(count)` – pobiera `count` bloków historycznych przez HTTP z obsługą błędów i opóźnieniami przeciw rate-limitingowi.
- `subscribe_new_heads()` – deleguje subskrypcję WebSocket do warstwy dostępu.

#### Warstwa Raportowania (`reporting_layer.py`)

Prezentuje dane użytkownikowi i zapisuje wyniki na dysk.

- `report_block(block_data, iteration)` – loguje dane bloku do konsoli i pliku `.log`.
- `report_transaction(tx_data, block_number)` – loguje dane transakcji oraz dopisuje wiersz do pliku CSV.
- `report_no_transactions()` – loguje informację o pustym bloku.
- `report_filtered_transaction()` – loguje informację o odfiltrowanej transakcji.
- `print_final_summary()` – loguje raport końcowy oraz zapisuje go do pliku `*_summary.txt`.

#### Filtry (`filters/transaction_filters.py`)

Implementują wzorzec strategii (Strategy Pattern) przez klasę abstrakcyjną `TransactionFilter`.

| Filtr | Opis |
|---|---|
| `GasPriceFilter(min_gwei)` | Przepuszcza TX z ceną gazu ≥ progu |
| `HighValueFilter(min_eth)` | Przepuszcza TX z wartością ≥ progu ETH |
| `HighFeeFilter(min_fee_eth)` | Przepuszcza TX z opłatą ≥ progu ETH |
| `WhaleTransactionFilter(min_eth)` | Przepuszcza TX „wielorybów" (≥ 10 ETH domyślnie) |
| `FailedTransactionFilter(only_failed)` | Przepuszcza TX zakończone błędem (`status=0`) |
| `ContractInteractionFilter(only_contracts)` | Przepuszcza TX do kontraktów (`to=None`) |
| `TokenTransferFilter` | Przepuszcza TX z danymi `input` (ERC-20) |
| `AddressFilter(address)` | Przepuszcza TX powiązane z podanym adresem |
| `FrequentSenderFilter(threshold)` | Przepuszcza TX od nadawcy po N-tym wystąpieniu |

---

## 2. Dokumentacja Niefunkcjonalna

### 2.1 Stos technologiczny

| Komponent | Technologia |
|---|---|
| Język programowania | Python 3.12+ |
| Komunikacja z blockchainem | `web3` 7.x (`Web3.HTTPProvider`, `websockets`) |
| Interfejs graficzny | PyQt6 |
| Testy jednostkowe | `pytest` |
| Asynchroniczność | `asyncio` (wbudowany) |
| Logowanie | `logging` (wbudowany) |
| Eksport danych | `csv` (wbudowany) |
| Zarządzanie środowiskiem | `python-dotenv` |
| Dostawca węzła | Alchemy (Sepolia testnet) |

### 2.2 Architektura

Aplikacja stosuje **model trójwarstwowy**:

```
┌─────────────────────────────────────────────────────┐
│                    GUI / main.py                    │  ← punkt wejścia
├─────────────────┬────────────────────────────────────┤
│  Reporting Layer│  ConsoleReporter                  │  ← prezentacja
├─────────────────┼────────────────────────────────────┤
│  Business Logic │  BlockchainLogic + Filters         │  ← przetwarzanie
├─────────────────┼────────────────────────────────────┤
│  Access Layer   │  BlockchainAccess (HTTP + WS)      │  ← komunikacja
└─────────────────┴────────────────────────────────────┘
                          │
                   Alchemy API (Sepolia)
```

Komunikacja między warstwami odbywa się **wyłącznie w dół** – GUI wywołuje logikę biznesową, logika wywołuje warstwę dostępu. Żadna niższa warstwa nie zna wyższej.

### 2.3 Połączenie z siecią

- **HTTP** (`web3.Web3.HTTPProvider`) – używane do pobierania bloków historycznych i danych transakcji. Zapewnia prostotę i niezawodność.
- **WebSocket** (`websockets`, protokół JSON-RPC `eth_subscribe newHeads`) – używane do monitorowania na żywo. Serwer _pcha_ dane natychmiast po pojawieniu się nowego bloku (brak pollingu).
- **Automatyczne wznawianie połączenia** – w przypadku zerwania WS aplikacja czeka `reconnect_delay` sekund i ponawia próbę nieskończenie.

### 2.4 Obsługa błędów i rate limiting

- Każde pobieranie bloku w `fetch_latest_blocks` otoczone jest blokiem `try/except`; błędy są logowane jako ostrzeżenia, a pętla kontynuuje.
- Między kolejnymi żądaniami HTTP stosowane jest opóźnienie `request_delay` (domyślnie 0,1 s) skonfigurowane w `AppConfig`, co zapobiega przekroczeniu limitów API.
- Błędy wewnątrz pętli WebSocket są łapane lokalnie, aby nie przerywać subskrypcji.

### 2.5 Metodologia pracy – uproszczony Scrum

- **Daily Scrum** – codzienne krótkie spotkania synchronizacyjne (15 min).
- **Feature branches** – każda funkcjonalność rozwijana na osobnej gałęzi (`feature/<nazwa>`).
- **Pull Requesty** – scalanie z `main` wyłącznie przez PR z co najmniej jedną recenzją.
- **Gałęzie projektu**: `main` (stabilna), `feature/access-layer`, `feature/business-logic`, `feature/reporting`, `feature/gui`, `feature/tests`.

### 2.6 Testy jednostkowe

Testy koncentrują się na **Warstwie Logiki Biznesowej** (`business_logic_layer.py`) – zgodnie z wymaganiami projektu.

- Framework: `pytest`
- Lokalizacja: `tests/test_business_logic_layer.py`, `tests/test_reporting_layer.py`
- Cel pokrycia: **≥ 70%** kodu warstwy logiki biznesowej
- Uruchomienie testów:

```bash
pytest tests/ -v
```

- Pokryte obszary:
  - `process_block_data` – pola, konwersja hashy, liczniki, timestampy
  - `process_transaction_data` – obliczenia, filtrowanie, adresy `None`, liczniki
  - `passes_filters` – wszystkie kombinacje filtrów
  - `get_aggregated_stats` – wartości zerowe i po przetwarzaniu
  - `get_live_analytics` – wszystkie metryki, średni czas bloku
  - `_process_block_with_tx` – blok z TX, bez TX, odfiltrowany TX
  - `fetch_latest_blocks` – zakres bloków, obsługa błędów, podział na subset TX

### 2.7 Struktura plików

```
C2D2-Blockchain-Monitor/
├── main.py                        # punkt wejścia – uruchamia GUI
├── gui.py                         # interfejs graficzny (PyQt6)
├── access_layer.py                # Warstwa Dostępu
├── business_logic_layer.py        # Warstwa Logiki Biznesowej
├── reporting_layer.py             # Warstwa Raportowania
├── config.py                      # ConnConfig, AppConfig
├── filters/
│   ├── __init__.py
│   └── transaction_filters.py     # filtry transakcji (Strategy Pattern)
├── tests/
│   ├── test_business_logic_layer.py
│   └── test_reporting_layer.py
├── logs/                          # generowane automatycznie
│   ├── DD-MM-YYYY-HH-MM-SS.log
│   ├── DD-MM-YYYY-HH-MM-SS_summary.txt
│   └── csv/
│       └── DD-MM-YYYY-HH-MM-SS.csv
├── requirements.txt
├── .gitignore
└── README.md
```

### 2.8 Konfiguracja

Klucz API przechowywany jest w pliku `.secret` (ignorowanym przez Git):

```
ALCHEMY_KEY=twój_klucz_api
```

Parametry aplikacji konfiguruje się w `config.py`:

| Parametr | Domyślna wartość | Opis |
|---|---|---|
| `blocks_to_fetch` | `100` | Liczba bloków historycznych pobieranych przy starcie |
| `reconnect_delay` | `5` | Czas oczekiwania przed ponownym połączeniem WS (sekundy) |
| `request_delay` | `0.1` | Opóźnienie między żądaniami HTTP (ochrona przed rate limiting) |

---

## 3. Instalacja i uruchomienie

### Wymagania

- Python 3.12+
- Konto na [Alchemy](https://alchemy.com) z kluczem API dla sieci Sepolia

### Kroki

```bash
# 1. Sklonuj repozytorium
git clone https://github.com/<org>/C2D2-Blockchain-Monitor.git
cd C2D2-Blockchain-Monitor

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Utwórz plik .secret z kluczem API
echo "ALCHEMY_KEY=twój_klucz" > .secret

# 4. Uruchom aplikację
python main.py

# 5. Uruchom testy
pytest tests/ -v
```

---

## 4. Podział zadań i harmonogram

Szacowany łączny czas pracy: **71 godzin** (4 osoby × ~17.5 h).

| Zadania | Szac. czas | Przypisanie |
|---|---|---|
| Łączenie z siecią Sepolia | 4 h | Adrian Żurawski |
| Zbieranie informacji z ostatnich N bloków | 8 h | Bartosz Sebastian |
| Nasłuchiwanie nowych bloków | 9 h | Bartosz Sebastian |
| Przetwarzanie informacji o bloku i transakcji | 10 h | Michał Kłyszko |
| Agregowanie danych | 6 h | Michał Kłyszko |
| Wyświetlanie statystyk w czasie rzeczywistym | 7 h | Wojciech Paradziński |
| Zapis rezultatów i danych historycznych do plików | 7 h | Wojciech Paradziński |
| Interface graficzny dla użytkowników | 20 h | Wojciech Paradziński, Michał Kłyszko, Adrian Żurawski |
