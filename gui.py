import sys
import asyncio
import threading
from decimal import Decimal
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton, QSplitter,
    QHeaderView, QStatusBar, QFrame, QGroupBox, QComboBox,
    QDoubleSpinBox, QLineEdit, QScrollArea, QSizePolicy, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPalette, QFont, QIcon, QLinearGradient
from PyQt6.QtWidgets import QCheckBox

from access_layer import BlockchainAccess
from business_logic_layer import BlockchainLogic
from reporting_layer import ConsoleReporter


# ─────────────────────────────────────────────
#  DARK THEME PALETTE
# ─────────────────────────────────────────────

COLORS = {
    "bg_primary":    "#0d1117",
    "bg_secondary":  "#161b22",
    "bg_tertiary":   "#21262d",
    "bg_hover":      "#30363d",
    "border":        "#30363d",
    "border_bright": "#484f58",
    "accent":        "#58a6ff",
    "accent_green":  "#3fb950",
    "accent_red":    "#f85149",
    "accent_yellow": "#e3b341",
    "accent_purple": "#bc8cff",
    "text_primary":  "#e6edf3",
    "text_secondary":"#8b949e",
    "text_muted":    "#484f58",
    "header_bg":     "#161b22",
    "row_alt":       "#161b22",
    "row_normal":    "#0d1117",
    "selection":     "#1f6feb33",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 12px;
}}

QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg_primary']};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_secondary']};
    padding: 8px 20px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['accent']};
    border-bottom: 2px solid {COLORS['accent']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_hover']};
    color: {COLORS['text_primary']};
}}

QTableWidget {{
    background-color: {COLORS['bg_primary']};
    alternate-background-color: {COLORS['row_alt']};
    gridline-color: {COLORS['border']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    selection-background-color: {COLORS['selection']};
    selection-color: {COLORS['text_primary']};
    font-size: 11px;
}}

QTableWidget::item {{
    padding: 5px 8px;
    border: none;
    color: {COLORS['text_primary']};
}}

QTableWidget::item:selected {{
    background-color: {COLORS['selection']};
    color: {COLORS['accent']};
}}

QHeaderView::section {{
    background-color: {COLORS['header_bg']};
    color: {COLORS['text_secondary']};
    padding: 8px 10px;
    border: none;
    border-right: 1px solid {COLORS['border']};
    border-bottom: 2px solid {COLORS['accent']};
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

QHeaderView::section:last {{
    border-right: none;
}}

QPushButton {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.5px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['border_bright']};
}}

QPushButton#start_btn {{
    background-color: #1a4a1a;
    border-color: {COLORS['accent_green']};
    color: {COLORS['accent_green']};
}}

QPushButton#start_btn:hover {{
    background-color: #245924;
}}

QPushButton#stop_btn {{
    background-color: #4a1a1a;
    border-color: {COLORS['accent_red']};
    color: {COLORS['accent_red']};
}}

QPushButton#stop_btn:hover {{
    background-color: #5e2020;
}}

QPushButton#clear_btn {{
    background-color: transparent;
    border-color: {COLORS['border']};
    color: {COLORS['text_secondary']};
    padding: 6px 14px;
    font-size: 11px;
}}

QPushButton#clear_btn:hover {{
    border-color: {COLORS['border_bright']};
    color: {COLORS['text_primary']};
}}

QLabel {{
    color: {COLORS['text_primary']};
    background: transparent;
}}

QLabel#section_title {{
    color: {COLORS['text_secondary']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}

QLabel#stat_value {{
    color: {COLORS['accent']};
    font-size: 18px;
    font-weight: 700;
}}

QLabel#stat_label {{
    color: {COLORS['text_secondary']};
    font-size: 10px;
    letter-spacing: 0.5px;
}}

QLabel#status_connected {{
    color: {COLORS['accent_green']};
    font-weight: 700;
    font-size: 11px;
}}

QLabel#status_disconnected {{
    color: {COLORS['accent_red']};
    font-weight: 700;
    font-size: 11px;
}}

QLabel#status_connecting {{
    color: {COLORS['accent_yellow']};
    font-weight: 700;
    font-size: 11px;
}}

QGroupBox {{
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_secondary']};
}}

QComboBox {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px 10px;
    min-width: 160px;
}}

QComboBox:hover {{
    border-color: {COLORS['border_bright']};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['bg_hover']};
}}

QDoubleSpinBox, QLineEdit {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px 10px;
}}

QDoubleSpinBox:hover, QLineEdit:hover {{
    border-color: {COLORS['border_bright']};
}}

QDoubleSpinBox:focus, QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

QScrollBar:vertical {{
    background: {COLORS['bg_primary']};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['bg_hover']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['border_bright']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QStatusBar {{
    background-color: {COLORS['bg_secondary']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_secondary']};
    font-size: 11px;
}}

QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 2px;
}}

QFrame#divider {{
    color: {COLORS['border']};
    background-color: {COLORS['border']};
    max-height: 1px;
}}
"""


# ─────────────────────────────────────────────
#  WORKER THREAD
# ─────────────────────────────────────────────

class MonitorWorker(QThread):
    block_received    = pyqtSignal(dict)
    tx_received       = pyqtSignal(dict, int)
    tx_filtered       = pyqtSignal(int)
    no_tx_in_block    = pyqtSignal(int)
    connected         = pyqtSignal(bool)
    error_occurred    = pyqtSignal(str)
    live_analytics    = pyqtSignal(dict)
    monitoring_done   = pyqtSignal(dict)
    status_msg        = pyqtSignal(str)

    def __init__(self, filters, block_count=10, initial_blocks=0, endless=False):
        super().__init__()
        self.filters = filters
        self.block_count = block_count
        self.initial_blocks = initial_blocks
        self.endless = endless
        self._stop_event = threading.Event()
        self.reporter = ConsoleReporter()

    def stop(self):
        self._stop_event.set()

    def run(self):
        asyncio.run(self._monitor())

    async def _monitor(self):
        try:
            async with BlockchainAccess() as access:
                logic = BlockchainLogic(access.w3, filters=self.filters)
                is_connected = await access.connect()
                self.connected.emit(is_connected)
                self.reporter.report_connection_status(is_connected)

                if not is_connected:
                    return

                # 🚀 KROK 1: ŁADOWANIE BLOKÓW HISTORYCZNYCH (Initial Blocks)
                if self.initial_blocks > 0:
                    self.status_msg.emit(f"📥 Loading {self.initial_blocks} history blocks...")
                    try:
                        latest_raw = await access.get_latest_block()
                        latest_num = latest_raw['number']
                        
                        # Ustalamy zakres bloków od najstarszego wstecz do bieżącego
                        start_num = max(0, latest_num - self.initial_blocks + 1)
                        
                        for b_num in range(start_num, latest_num + 1):
                            if self._stop_event.is_set():
                                break
                                
                            self.status_msg.emit(f"📥 Fetching history block #{b_num}...")
                            # Pobieramy konkretny blok po numerze
                            block = await access.w3.eth.get_block(b_num)
                            
                            processed_block = logic.process_block_data(block)
                            self.reporter.report_block(processed_block, b_num)
                            self.block_received.emit(processed_block)

                            if processed_block['transactions_count'] > 0:
                                latest_tx_hash = block['transactions'][-1]
                                raw_tx = await access.get_transaction(latest_tx_hash)
                                raw_receipt = await access.get_transaction_receipt(latest_tx_hash)
                                processed_tx = logic.process_transaction_data(raw_tx, raw_receipt)

                                if processed_tx:
                                    self.reporter.report_transaction(processed_tx, processed_block['number'])
                                    self.tx_received.emit(processed_tx, processed_block['number'])
                                else:
                                    self.tx_filtered.emit(processed_block['number'])
                            else:
                                self.reporter.report_no_transactions()
                                self.no_tx_in_block.emit(processed_block['number'])
                                
                            self.live_analytics.emit(logic.get_live_analytics())
                            await asyncio.sleep(0.2) # Małe opóźnienie, by interfejs oddychał
                            
                    except Exception as hist_err:
                        print(f"History loading warning: {hist_err}")

                # 🚀 KROK 2: MONITOROWANIE NA ŻYWO NOWYCH BLOKÓW
                self.status_msg.emit("👀 Listening for new live blocks...")
                
                # Pobieramy najświeższy numer początkowy po załadowaniu historii
                try:
                    last_b = await access.get_latest_block()
                    latest_block = last_b['number']
                except:
                    latest_block = 0

                i = 0
                while (self.endless or i < self.block_count) and not self._stop_event.is_set():
                    raw_block = await access.get_latest_block()
                    while raw_block['number'] == latest_block and not self._stop_event.is_set():
                        await asyncio.sleep(1)
                        raw_block = await access.get_latest_block()

                    if self._stop_event.is_set():
                        break

                    latest_block = raw_block['number']
                    processed_block = logic.process_block_data(raw_block)
                    self.reporter.report_block(processed_block, i + 1)
                    self.block_received.emit(processed_block)

                    if processed_block['transactions_count'] > 0:
                        latest_tx_hash = raw_block['transactions'][-1]
                        raw_tx = await access.get_transaction(latest_tx_hash)
                        raw_receipt = await access.get_transaction_receipt(latest_tx_hash)
                        processed_tx = logic.process_transaction_data(raw_tx, raw_receipt)

                        if processed_tx:
                            self.reporter.report_transaction(processed_tx, processed_block['number'])
                            self.tx_received.emit(processed_tx, processed_block['number'])
                        else:
                            logic.increment_filtered_counter()
                            self.tx_filtered.emit(processed_block['number'])
                    else:
                        self.reporter.report_no_transactions()
                        self.no_tx_in_block.emit(processed_block['number'])

                    self.live_analytics.emit(logic.get_live_analytics())
                    i += 1
                    await asyncio.sleep(2)

                self.reporter.print_final_summary()
                self.monitoring_done.emit(logic.get_aggregated_stats())

        except Exception as e:
            self.error_occurred.emit(str(e))


# ─────────────────────────────────────────────
#  STAT CARD WIDGET
# ─────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, label, value="0", accent_color=None):
        super().__init__()
        self.accent = accent_color or COLORS['accent']

        self.setObjectName("stat_card")
        self.setStyleSheet(f"""
            QFrame#stat_card {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-top: 2px solid {self.accent};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.value_lbl = QLabel(value)
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.value_lbl.setStyleSheet(f"""
            color: {self.accent};
            font-size: 20px;
            font-weight: 700;
        """)

        self.label_lbl = QLabel(label)
        self.label_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_lbl.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        """)

        layout.addWidget(self.label_lbl)
        layout.addWidget(self.value_lbl)

    def set_value(self, val):
        self.value_lbl.setText(str(val))


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────

class BlockchainMonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.block_count = 0
        self.tx_count = 0
        self.filtered_count = 0
        self.total_eth = Decimal('0')
        self.total_gas = 0

        self.setWindowTitle("Sepolia Blockchain Monitor Advanced")
        self.setMinimumSize(1240, 780)
        self.resize(1440, 880)

        self._setup_ui()
        self._apply_theme()

    # ──────────────── UI SETUP ────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        root.addWidget(self._build_header())

        # Stats row
        root.addWidget(self._build_stats_bar())

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        root.addWidget(div)

        # Main content
        content = QHBoxLayout()
        content.setContentsMargins(12, 12, 12, 12)
        content.setSpacing(12)

        # Left: tables and analytics
        tabs_widget = self._build_tables_and_tabs()
        content.addWidget(tabs_widget, stretch=1)

        # Right: filters/controls panel
        content.addWidget(self._build_controls(), stretch=0)

        root.addLayout(content)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Ready to connect", COLORS['text_secondary'])

    def _build_header(self):
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-bottom: 1px solid {COLORS['border']};
                min-height: 52px;
                max-height: 52px;
            }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        title_lbl = QLabel("Sepolia Blockchain Monitor")
        title_lbl.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 1px;
        """)

        self.conn_status = QLabel("● Disconnected")
        self.conn_status.setObjectName("status_disconnected")

        layout.addWidget(title_lbl)
        layout.addSpacing(16)
        layout.addStretch()
        layout.addWidget(self.conn_status)

        return header

    def _build_stats_bar(self):
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-bottom: 1px solid {COLORS['border']};
                min-height: 78px;
                max-height: 78px;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        self.stat_blocks  = StatCard("Blocks",        "0",   COLORS['accent'])
        self.stat_txs     = StatCard("Transactions",   "0",   COLORS['accent_green'])
        self.stat_flt     = StatCard("Filtered",       "0",   COLORS['accent_yellow'])
        self.stat_eth     = StatCard("Total ETH",      "0.000000", COLORS['accent_purple'])
        self.stat_gas     = StatCard("Total Gas",      "0",   "#f0883e")

        for card in [self.stat_blocks, self.stat_txs, self.stat_flt, self.stat_eth, self.stat_gas]:
            layout.addWidget(card)

        return bar

    def _build_tables_and_tabs(self):
        tabs = QTabWidget()

        # ── Blocks tab ──
        blocks_widget = QWidget()
        bv = QVBoxLayout(blocks_widget)
        bv.setContentsMargins(0, 8, 0, 0)
        bv.setSpacing(6)

        # Nagłówek dla bloków (Tytuł + Szukajka w jednej linii)
        block_header_layout = QHBoxLayout()
        
        blocks_label = QLabel("BLOCKS HISTORY")
        blocks_label.setObjectName("section_title")
        block_header_layout.addWidget(blocks_label)

        self.blocks_search = QLineEdit()
        self.blocks_search.setPlaceholderText("🔍 Search by block number")
        self.blocks_search.setFixedWidth(200)
        self.blocks_search.textChanged.connect(self._filter_blocks_table)
        block_header_layout.addWidget(self.blocks_search)
        
        bv.addLayout(block_header_layout)

        self.blocks_table = self._make_table([
            "BLOCK NUMBER",
            "HASH",
            "TRANSACTIONS",
            "TIMESTAMP"
        ], [170, 480, 170, 50])
        bv.addWidget(self.blocks_table)
        tabs.addTab(blocks_widget, "📦  Blocks")

        # ── Transactions tab ──
        tx_widget = QWidget()
        tv = QVBoxLayout(tx_widget)
        tv.setContentsMargins(0, 8, 0, 0)
        tv.setSpacing(6)

        tx_header_layout = QHBoxLayout()

        tx_label = QLabel("TRANSACTIONS (RECENT FROM EACH BLOCK)")
        tx_label.setObjectName("section_title")
        tx_header_layout.addWidget(tx_label)

        self.tx_search = QLineEdit()
        self.tx_search.setPlaceholderText("🔍 Search by block number")
        self.tx_search.setFixedWidth(200)
        self.tx_search.textChanged.connect(self._filter_tx_table)
        tx_header_layout.addWidget(self.tx_search)
        
        tv.addLayout(tx_header_layout)

        self.tx_table = self._make_table([
            "BLOCK",
            "TX HASH",
            "SENDER",
            "RECEIVER",
            "ETH",
            "GAS USED",
            "GAS PRICE",
            "ETH FEE"
        ], [80, 240, 180, 180, 100, 100, 120, 120])
        tv.addWidget(self.tx_table)
        tabs.addTab(tx_widget, "🔄  Transactions")

        # ── Analytics tab ──
        analytics_widget = QWidget()
        av = QVBoxLayout(analytics_widget)
        av.setContentsMargins(0, 8, 0, 0)
        av.setSpacing(6)

        analytics_label = QLabel("LIVE BLOCKCHAIN AGGREGATED METRICS")
        analytics_label.setObjectName("section_title")
        av.addWidget(analytics_label)

        self.analytics_table = self._make_table([
            "METRIC / AGGREGATION", 
            "LIVE VALUE"
        ], [400, 200])
        
        # Inicjalizacja stałych wierszy metryk
        self.metric_keys = [
            ("Average Block Time", "avg_block_time"),
            ("Average Fee per Transaction", "avg_fee_tx"),
            ("Average Transferred ETH per TX", "avg_eth_tx"),
            ("Average Transactions per Block", "avg_tx_per_block"),
            ("Average Gas used per Block", "avg_gas_per_block"),
            ("Total Fee Pool Captured", "total_fees_pool"),
            ("Unique Senders Active", "unique_senders"),
            ("Unique Receivers Active", "unique_receivers")
        ]
        
        self.analytics_table.setRowCount(len(self.metric_keys))
        for row, (label, _) in enumerate(self.metric_keys):
            lbl_item = QTableWidgetItem(label)
            lbl_item.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
            val_item = QTableWidgetItem("0.00")
            val_item.setForeground(QColor(COLORS['accent']))
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            self.analytics_table.setItem(row, 0, lbl_item)
            self.analytics_table.setItem(row, 1, val_item)
            
        av.addWidget(self.analytics_table)
        tabs.addTab(analytics_widget, "📊  Analytics")

        return tabs

    def _make_table(self, headers, col_widths):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setShowGrid(True)
        table.verticalHeader().setVisible(False)
        table.setWordWrap(False)
        table.setSortingEnabled(False)

        for i, w in enumerate(col_widths):
            table.setColumnWidth(i, w)

        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(30)

        return table

    def _build_controls(self):
        panel = QFrame()
        panel.setFixedWidth(360)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # ── Start/Stop ──
        ctrl_lbl = QLabel("CONTROL PANEL")
        ctrl_lbl.setObjectName("section_title")
        layout.addWidget(ctrl_lbl)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self._start_monitoring)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_monitoring)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row)

        self.clear_btn = QPushButton("Clear table")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self._clear_tables)
        layout.addWidget(self.clear_btn)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(div)

        # ── 🚀 PODWÓJNE POLE: BLOCKS AMOUNT & INITIAL BLOCKS ──
        blocks_config_row = QHBoxLayout()
        
        blk_grp = QGroupBox("BLOCKS LIVE")
        blk_lyt = QVBoxLayout(blk_grp)
        self.block_count_spin = QDoubleSpinBox()
        self.block_count_spin.setDecimals(0)
        self.block_count_spin.setRange(1, 1000)
        self.block_count_spin.setValue(10)
        self.block_count_spin.setStyleSheet("font-size: 11px;")
        blk_lyt.addWidget(self.block_count_spin)
        
        self.endless_checkbox = QCheckBox("Listen endlessly")
        self.endless_checkbox.toggled.connect(lambda checked: self.block_count_spin.setDisabled(checked))
        blk_lyt.addWidget(self.endless_checkbox)

        init_grp = QGroupBox("INITIAL BACK")
        init_lyt = QVBoxLayout(init_grp)
        self.initial_blocks_spin = QDoubleSpinBox()
        self.initial_blocks_spin.setDecimals(0)
        self.initial_blocks_spin.setRange(0, 100)
        self.initial_blocks_spin.setValue(10) # Domyślnie wgraj 10 ostatnich bloków
        self.initial_blocks_spin.setStyleSheet("font-size: 11px;")
        init_lyt.addWidget(self.initial_blocks_spin)
        
        blocks_config_row.addWidget(blk_grp)
        blocks_config_row.addWidget(init_grp)
        layout.addLayout(blocks_config_row)

        # ── Filter ──
        flt_grp = QGroupBox("TRANSACTION FILTER")
        flt_lyt = QVBoxLayout(flt_grp)
        flt_lyt.setSpacing(8)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "No filter",
            "Gas Price (min Gwei)",
            "High value (min ETH)",
            "High fee (min ETH)",
            "Whale (min ETH)",
            "Failed transactions",
            "Contract interactions",
            "Tokens transfer",
            "Address filter",
        ])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        flt_lyt.addWidget(self.filter_combo)

        self.filter_value_spin = QDoubleSpinBox()
        self.filter_value_spin.setDecimals(4)
        self.filter_value_spin.setRange(0, 100000)
        self.filter_value_spin.setValue(0.03)
        self.filter_value_spin.setPrefix("Threshold: ")
        flt_lyt.addWidget(self.filter_value_spin)

        self.filter_address = QLineEdit()
        self.filter_address.setPlaceholderText("0x… (only address filter)")
        self.filter_address.setVisible(False)
        flt_lyt.addWidget(self.filter_address)

        layout.addWidget(flt_grp)

        # ── Live log ──
        log_grp = QGroupBox("LOGS")
        log_lyt = QVBoxLayout(log_grp)
        self.log_label = QLabel("—")
        self.log_label.setWordWrap(True)
        self.log_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.log_label.setFixedHeight(120)
        self.log_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        log_lyt.addWidget(self.log_label)
        layout.addWidget(log_grp)

        layout.addStretch()

        ver_lbl = QLabel("Sepolia Blockchain Monitor")
        ver_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px;")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_lbl)

        return panel

    def _apply_theme(self):
        self.setStyleSheet(STYLESHEET)

    def _on_filter_changed(self, idx):
        address_filter = (idx == 8)
        spinbox_filters = idx in [1, 2, 3, 4]
        self.filter_address.setVisible(address_filter)
        self.filter_value_spin.setVisible(spinbox_filters)

        prefixes = {
            1: "Min Gwei: ", 2: "Min ETH: ",
            3: "Min ETH: ", 4: "Min ETH: "
        }
        if idx in prefixes:
            self.filter_value_spin.setPrefix(prefixes[idx])

    def _filter_blocks_table(self, text):
        text = text.strip().lower()
        for row in range(self.blocks_table.rowCount()):
            item = self.blocks_table.item(row, 0)
            if item:
                self.blocks_table.setRowHidden(row, text not in item.text().lower())

    def _filter_tx_table(self, text):
        text = text.strip().lower()
        for row in range(self.tx_table.rowCount()):
            block_item = self.tx_table.item(row, 0)
            hash_item = self.tx_table.item(row, 1)
            
            show_row = False
            if block_item and text in block_item.text().lower():
                show_row = True
            if hash_item and text in hash_item.text().lower():
                show_row = True
                
            self.tx_table.setRowHidden(row, not show_row)

    def _on_block_double_clicked(self, item):
        if item.column() == 0:  # Kliknięcie w kolumnę z numerem bloku
            block_num = item.text()
            self.tx_search.setText(block_num)
            self.tabs_widget.setCurrentIndex(1)

    def _on_tx_double_clicked(self, item):
        if item.column() == 0:  # Kliknięcie w kolumnę z numerem bloku
            block_num = item.text()
            self.blocks_search.setText(block_num)
            self.tabs_widget.setCurrentIndex(0)


    def _get_selected_filters(self):
        idx = self.filter_combo.currentIndex()
        val = self.filter_value_spin.value()
        addr = self.filter_address.text().strip()

        from filters import (
            GasPriceFilter, HighValueFilter, HighFeeFilter, WhaleTransactionFilter,
            FailedTransactionFilter, ContractInteractionFilter, TokenTransferFilter, AddressFilter
        )

        mapping = {
            0: [],
            1: [GasPriceFilter(val)],
            2: [HighValueFilter(val)],
            3: [HighFeeFilter(val)],
            4: [WhaleTransactionFilter(val)],
            5: [FailedTransactionFilter(True)],
            6: [ContractInteractionFilter(True)],
            7: [TokenTransferFilter()],
            8: [AddressFilter(addr)] if addr else [],
        }
        return mapping.get(idx, [])

    # ──────────────── SLOTS: Control ────────────────

    def _start_monitoring(self):
        if hasattr(self, 'worker') and self.worker is not None:
            if self.worker.isRunning():
                self.worker._stop_event.set()
                self.worker.wait()

        self.total_blocks = 0
        self.total_txs = 0
        self.filtered_count = 0
        self.total_eth = Decimal('0')
        self.total_gas = 0
        self._update_stats()

        filters = self._get_selected_filters()
        block_count = int(self.block_count_spin.value())
        initial_blocks = int(self.initial_blocks_spin.value())
        is_endless = self.endless_checkbox.isChecked()

        # Przekazujemy oba parametry konfiguracyjne do workera
        self.worker = MonitorWorker(filters, block_count, initial_blocks, endless=is_endless)
        self.worker.block_received.connect(self._on_block)
        self.worker.tx_received.connect(self._on_tx)
        self.worker.tx_filtered.connect(self._on_tx_filtered)
        self.worker.no_tx_in_block.connect(self._on_no_tx)
        self.worker.connected.connect(self._on_connected)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.live_analytics.connect(self._on_live_analytics)
        self.worker.status_msg.connect(self._on_status_msg)
        self.worker.monitoring_done.connect(self._on_done)

        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_status("⏳ Connecting to Sepolia…", COLORS['accent_yellow'])
        self._log("Starting pipeline...")
        self.conn_status.setText("● Connecting…")
        self.conn_status.setObjectName("status_connecting")
        self.conn_status.setStyleSheet(f"color: {COLORS['accent_yellow']}; font-weight: 700;")

    def _stop_monitoring(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.setEnabled(False)
        self._log("Stopped by user.")
        self._set_status("Stopped", COLORS['text_secondary'])

    def _clear_tables(self):
        self.blocks_table.setRowCount(0)
        self.tx_table.setRowCount(0)
        self.blocks_search.clear()
        self.tx_search.clear()
        
        # Reset zakładki analitycznej
        for row in range(self.analytics_table.rowCount()):
            self.analytics_table.item(row, 1).setText("0.00")
            
        self.block_count = 0
        self.tx_count = 0
        self.filtered_count = 0
        self.total_eth = Decimal('0')
        self.total_gas = 0
        self._update_stats()
        self._log("Tables cleared.")

    # ──────────────── SLOTS: Worker signals ────────────────

    def _on_status_msg(self, text):
        self._set_status(text, COLORS['accent_yellow'])

    def _on_live_analytics(self, analytics_dict):
        """Slot odbierający dane o agregacji i nanoszący je na trzecią zakładkę."""
        for row, (_, dict_key) in enumerate(self.metric_keys):
            if dict_key in analytics_dict:
                val = analytics_dict[dict_key]
                self.analytics_table.item(row, 1).setText(val)

    def _on_connected(self, ok):
        if ok:
            self.conn_status.setText("● Connected")
            self.conn_status.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: 700;")
            self._set_status("✅ Connected to Sepolia", COLORS['accent_green'])
            self._log("✔ Connected to Sepolia!")
        else:
            self.conn_status.setText("● Connection Error")
            self.conn_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-weight: 700;")
            self._set_status("❌ Connection Error", COLORS['accent_red'])
            self._log("✘ Cannot connect to Sepolia.")
            self._reset_buttons()

    def _on_block(self, block_data):
        self.block_count += 1
        self.blocks_table.insertRow(0)

        num_item = QTableWidgetItem(str(block_data['number']))
        num_item.setForeground(QColor(COLORS['accent']))
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        hash_item = QTableWidgetItem(block_data['hash'])
        hash_item.setForeground(QColor(COLORS['text_secondary']))

        tx_item = QTableWidgetItem(str(block_data['transactions_count']))
        tx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if block_data['transactions_count'] > 0:
            tx_item.setForeground(QColor(COLORS['accent_green']))
        else:
            tx_item.setForeground(QColor(COLORS['text_muted']))

        time_item = QTableWidgetItem(datetime.now().strftime("%H:%M:%S"))
        time_item.setForeground(QColor(COLORS['text_secondary']))
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.blocks_table.setItem(0, 0, num_item)
        self.blocks_table.setItem(0, 1, hash_item)
        self.blocks_table.setItem(0, 2, tx_item)
        self.blocks_table.setItem(0, 3, time_item)
        self.blocks_table.scrollToTop()

        self._update_stats()
        self._log(f"📦 Block #{block_data['number']} • {block_data['transactions_count']} tx")

    def _on_tx(self, tx_data, block_number):
        self.tx_count += 1
        eth_val = Decimal(str(tx_data['amount_eth']))
        fee_val = Decimal(str(tx_data['fee_eth']))
        self.total_eth += eth_val
        self.total_gas += tx_data['gas_used']
        self.tx_table.insertRow(0)

        def cell(text, color=None, align=None):
            item = QTableWidgetItem(str(text))
            if color:
                item.setForeground(QColor(color))
            if align:
                item.setTextAlignment(align)
            return item

        center = Qt.AlignmentFlag.AlignCenter

        blk_item = cell(str(block_number), COLORS['accent'], center)
        hash_item = cell(tx_data['hash'], COLORS['text_secondary'])
        hash_item.setToolTip(tx_data['hash'])

        sender_item = cell(tx_data['sender'], COLORS['accent_yellow'])
        sender_item.setToolTip(tx_data['sender'])

        recv = tx_data['receiver'] or "—"
        recv_short = (recv) if len(recv) > 20 else recv
        recv_item = cell(recv_short, COLORS['text_primary'])
        recv_item.setToolTip(recv)

        eth_item = cell(f"{float(eth_val):.9f}", COLORS['accent_green'], center)
        gas_item = cell(str(tx_data['gas_used']), COLORS['text_secondary'], center)

        gas_price_gwei = float(tx_data['gas_price_wei']) / 1e9
        gas_price_item = cell(f"{gas_price_gwei:.4f}", COLORS['text_secondary'], center)

        fee_item = cell(f"{float(fee_val):.9f}", "#f0883e", center)

        for col, item in enumerate([blk_item, hash_item, sender_item, recv_item,
                                    eth_item, gas_item, gas_price_item, fee_item]):
            self.tx_table.setItem(0, col, item)

        self.tx_table.scrollToTop()
        self._update_stats()
        self._log(f"🔄 TX #{self.tx_count} • {float(eth_val):.4f} ETH")

    def _on_tx_filtered(self, block_number):
        self.filtered_count += 1
        self._update_stats()
        self._log(f"⚡ Block #{block_number} • tx filtered")

    def _on_no_tx(self, block_number):
        self._log(f"📭 Block #{block_number} • no transactions")

    def _on_error(self, msg):
        self._set_status(f"❌ Error: {msg}", COLORS['accent_red'])
        self._log(f"✘ Error: {msg[:60]}")
        self._reset_buttons()

    def _on_done(self, stats):
        self._set_status(
            f"✅ Finished | {stats['summary_blocks_processed']} blocks | "
            f"{stats['summary_transactions_monitored']} transactions",
            COLORS['accent_green']
        )
        self._log(f"✔ Ready! {stats['summary_blocks_processed']} blocks synced.")
        self.conn_status.setText("● Not connected")
        self.conn_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-weight: 700;")
        self._reset_buttons()

    # ──────────────── HELPERS ────────────────

    def _update_stats(self):
        self.stat_blocks.set_value(str(self.block_count))
        self.stat_txs.set_value(str(self.tx_count))
        self.stat_flt.set_value(str(self.filtered_count))
        self.stat_eth.set_value(f"{float(self.total_eth):.6f}")
        self.stat_gas.set_value(f"{self.total_gas:,}")

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        current = self.log_label.text()
        lines = current.split("\n") if current != "—" else []
        lines.insert(0, f"[{ts}] {msg}")
        self.log_label.setText("\n".join(lines[:8]))

    def _set_status(self, msg, color):
        self.status_bar.showMessage(msg)
        self.status_bar.setStyleSheet(f"color: {color};")

    def _reset_buttons(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(COLORS['bg_primary']))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Base,            QColor(COLORS['bg_secondary']))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(COLORS['bg_tertiary']))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(COLORS['bg_tertiary']))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Text,            QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Button,          QColor(COLORS['bg_tertiary']))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(COLORS['accent']))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = BlockchainMonitorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()