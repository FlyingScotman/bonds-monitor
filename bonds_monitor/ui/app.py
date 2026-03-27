"""Main Textual TUI application."""
from __future__ import annotations

from datetime import date
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)
from textual.timer import Timer

from bonds_monitor.engine import Engine
from bonds_monitor.models import BondDisplayRow


# ---------------------------------------------------------------------------
# Bond detail popup
# ---------------------------------------------------------------------------

class BondDetailScreen(ModalScreen):
    """Full-screen popup showing all data for a single bond."""

    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close")]

    def __init__(self, row: BondDisplayRow):
        super().__init__()
        self._row = row

    def compose(self) -> ComposeResult:
        r = self._row

        def fmt_pct(v: Optional[float], decimals: int = 4) -> str:
            return f"{v:.{decimals}f}" if v is not None else "—"

        def fmt_yld(v: Optional[float]) -> str:
            return f"{v*100:.2f}%" if v is not None else "—"

        lines = [
            f"  ISIN:          {r.isin}",
            f"  Name:          {r.short_name}",
            f"  Currency:      {r.currency}",
            f"  Maturity:      {r.maturity.strftime('%d.%m.%Y')}",
            f"",
            f"  ── Raw RUB Orderbook ──────────────────",
            f"  Bid (RUB):     {fmt_pct(r.bid)}",
            f"  Ask (RUB):     {fmt_pct(r.ask)}",
            f"",
            f"  ── Converted HCY Prices ───────────────",
            f"  Conv Bid:      {fmt_pct(r.conv_bid)}  {'[OVERRIDE]' if r.px_overridden else ''}",
            f"  Conv Ask:      {fmt_pct(r.conv_ask)}",
            f"",
            f"  ── Analytics ──────────────────────────",
            f"  Bid Yield:     {fmt_yld(r.bid_yield)}",
            f"  Ask Yield:     {fmt_yld(r.ask_yield)}",
            f"  Duration:      {fmt_pct(r.duration, 2)}",
            f"  Z-spread:      {f'{r.z_spread:.0f} bps' if r.z_spread is not None else '—'}",
            f"",
            f"  ── Extra ──────────────────────────────",
            f"  Volume (MM):   {fmt_pct(r.volume_rub_mm, 1)}",
            f"  Repo Rate:     {f'{r.avg_repo_rate:.2f}%' if r.avg_repo_rate else '—'}",
        ]

        with Container(id="detail-box"):
            yield Static(f"\n  Bond Detail — {r.short_name}\n", id="detail-title")
            yield Static("\n".join(lines), id="detail-body")
            yield Static("\n  [ESC / q] Close", id="detail-footer")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Main bond table
# ---------------------------------------------------------------------------

COLUMN_FORMATTERS = {
    "short_name":  lambda r: r.short_name,
    "isin":        lambda r: r.isin,
    "currency":    lambda r: r.currency,
    "maturity":    lambda r: r.maturity.strftime("%m.%Y"),
    "bid":         lambda r: f"{r.bid:.3f}"      if r.bid      is not None else "—",
    "ask":         lambda r: f"{r.ask:.3f}"      if r.ask      is not None else "—",
    "conv_bid":    lambda r: (f"*{r.conv_bid:.3f}" if r.px_overridden else f"{r.conv_bid:.3f}") if r.conv_bid is not None else "—",
    "conv_ask":    lambda r: (f"*{r.conv_ask:.3f}" if r.px_overridden else f"{r.conv_ask:.3f}") if r.conv_ask is not None else "—",
    "bid_yield":   lambda r: f"{r.bid_yield*100:.2f}%"  if r.bid_yield  is not None else "—",
    "ask_yield":   lambda r: f"{r.ask_yield*100:.2f}%"  if r.ask_yield  is not None else "—",
    "duration":    lambda r: f"{r.duration:.2f}"        if r.duration   is not None else "—",
    "z_spread":    lambda r: f"{r.z_spread:.0f}"        if r.z_spread   is not None else "—",
    "volume":      lambda r: f"{r.volume_rub_mm:.0f}"   if r.volume_rub_mm is not None else "—",
    "repo_rate":   lambda r: f"{r.avg_repo_rate:.1f}%"  if r.avg_repo_rate is not None else "—",
}


class BondsApp(App):
    """Bonds monitoring TUI."""

    CSS = """
    Screen {
        background: $surface;
    }
    #status-bar {
        height: 1;
        background: $boost;
        color: $text-muted;
        padding: 0 2;
    }
    #search-bar {
        height: 3;
        display: none;
        layout: horizontal;
        padding: 0 1;
        align: left middle;
    }
    #search-bar.visible {
        display: block;
    }
    #search-bar Label {
        width: auto;
        padding: 0 1;
    }
    #search-bar Input {
        width: 1fr;
    }
    #detail-box {
        background: $panel;
        border: round $primary;
        padding: 1 2;
        margin: 4 8;
        height: auto;
        max-height: 90vh;
    }
    #detail-title {
        color: $primary;
        text-style: bold;
    }
    #detail-footer {
        color: $text-muted;
        margin-top: 1;
    }
    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("j",       "move_down",     "Down",        show=False),
        Binding("k",       "move_up",       "Up",          show=False),
        Binding("ctrl+d",  "page_down",     "Page Down",   show=False),
        Binding("ctrl+u",  "page_up",       "Page Up",     show=False),
        Binding("g",       "go_top",        "Top",         show=False),
        Binding("G",       "go_bottom",     "Bottom",      show=False),
        Binding("/",       "search",        "Search",      show=True),
        Binding("n",       "search_next",   "Next match",  show=False),
        Binding("N",       "search_prev",   "Prev match",  show=False),
        Binding("enter",   "show_detail",   "Detail",      show=True),
        Binding("r",       "refresh",       "Refresh",     show=True),
        Binding("a",       "toggle_auto",   "Auto",        show=True),
        Binding("o",       "override_px",   "Override Px", show=True),
        Binding("ctrl+r",  "reset_override","Reset Ovr",   show=False),
        Binding("1",       "tab_1",         "Tab 1",       show=False),
        Binding("2",       "tab_2",         "Tab 2",       show=False),
        Binding("3",       "tab_3",         "Tab 3",       show=False),
        Binding("4",       "tab_4",         "Tab 4",       show=False),
        Binding("q",       "quit",          "Quit",        show=True),
    ]

    def __init__(self, engine: Engine, config: dict):
        super().__init__()
        self._engine = engine
        self._config = config
        self._rows: list[BondDisplayRow] = []
        self._filtered_rows: list[BondDisplayRow] = []
        self._refresh_timer: Optional[Timer] = None
        self._auto_on: bool = True   # whether auto-refresh is enabled
        self._search_query: str = ""
        self._search_matches: list[int] = []
        self._search_idx: int = 0
        self._current_tab_idx: int = 0
        self._tabs = config.get("tabs", [{"name": "All", "filter": {}, "sort": "maturity"}])
        self._col_defs = config.get("display", {}).get("columns", [])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("", id="status-bar")
            yield DataTable(id="bond-table", cursor_type="row")
            with Container(id="search-bar"):
                yield Label("/  ")
                yield Input(placeholder="search...", id="search-input")
        yield Footer()

    def on_mount(self) -> None:
        self._setup_table()
        self._do_refresh()
        self._schedule_auto_refresh()

    # ------------------------------------------------------------------
    # Table setup
    # ------------------------------------------------------------------

    def _setup_table(self) -> None:
        table: DataTable = self.query_one("#bond-table", DataTable)
        table.clear(columns=True)
        for col in self._col_defs:
            table.add_column(col["label"], key=col["id"], width=col.get("width"))

    def _populate_table(self) -> None:
        table: DataTable = self.query_one("#bond-table", DataTable)
        table.clear()
        for row in self._filtered_rows:
            values = [COLUMN_FORMATTERS.get(col["id"], lambda r: "")(row) for col in self._col_defs]
            # Highlight overridden rows
            style = "bold yellow" if row.px_overridden else None
            table.add_row(*values, key=row.isin)

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def _do_refresh(self) -> None:
        try:
            self._rows = self._engine.refresh()
        except Exception as e:
            self._set_status(f"Refresh error: {e}", error=True)
            return
        self._apply_tab_filter()
        self._populate_table()
        self._set_status(f"Updated — {len(self._filtered_rows)} bonds  |  Tab: {self._current_tab['name']}  |  Auto: {'ON' if self._auto_on else 'OFF'}")

    def _apply_tab_filter(self) -> None:
        tab = self._current_tab
        f = tab.get("filter", {})
        rows = self._rows

        if f.get("currency"):
            rows = [r for r in rows if r.currency == f["currency"]]
        if f.get("max_duration") is not None:
            rows = [r for r in rows if r.duration is not None and r.duration <= f["max_duration"]]

        sort_key = tab.get("sort", "maturity")
        if sort_key == "maturity":
            rows = sorted(rows, key=lambda r: r.maturity)
        elif sort_key == "duration":
            rows = sorted(rows, key=lambda r: r.duration or 999)

        # Apply active search filter
        if self._search_query:
            q = self._search_query.lower()
            rows = [r for r in rows if q in r.short_name.lower() or q in r.isin.lower()]

        self._filtered_rows = rows

    def _schedule_auto_refresh(self) -> None:
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
        if self._auto_on:
            interval = self._config.get("refresh", {}).get("interval_seconds", 10)
            self._refresh_timer = self.set_interval(interval, self._do_refresh)

    @property
    def _current_tab(self) -> dict:
        return self._tabs[self._current_tab_idx % len(self._tabs)]

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, msg: str, error: bool = False) -> None:
        bar = self.query_one("#status-bar", Static)
        bar.update(msg)

    # ------------------------------------------------------------------
    # Key actions
    # ------------------------------------------------------------------

    def action_move_down(self) -> None:
        self.query_one("#bond-table", DataTable).action_scroll_down()

    def action_move_up(self) -> None:
        self.query_one("#bond-table", DataTable).action_scroll_up()

    def action_page_down(self) -> None:
        table = self.query_one("#bond-table", DataTable)
        for _ in range(10):
            table.action_scroll_down()

    def action_page_up(self) -> None:
        table = self.query_one("#bond-table", DataTable)
        for _ in range(10):
            table.action_scroll_up()

    def action_go_top(self) -> None:
        table = self.query_one("#bond-table", DataTable)
        if table.row_count:
            table.move_cursor(row=0)

    def action_go_bottom(self) -> None:
        table = self.query_one("#bond-table", DataTable)
        if table.row_count:
            table.move_cursor(row=table.row_count - 1)

    def action_refresh(self) -> None:
        self._do_refresh()

    def action_toggle_auto(self) -> None:
        self._auto_on = not self._auto_on
        self._schedule_auto_refresh()
        self._set_status(f"Auto refresh: {'ON' if self._auto_on else 'OFF'}")

    def action_show_detail(self) -> None:
        table = self.query_one("#bond-table", DataTable)
        row_key = table.cursor_row
        if row_key < 0 or row_key >= len(self._filtered_rows):
            return
        row = self._filtered_rows[row_key]
        self.push_screen(BondDetailScreen(row))

    def action_search(self) -> None:
        bar = self.query_one("#search-bar", Container)
        bar.add_class("visible")
        self.query_one("#search-input", Input).focus()

    def action_search_next(self) -> None:
        if self._search_matches:
            self._search_idx = (self._search_idx + 1) % len(self._search_matches)
            self._jump_to_match()

    def action_search_prev(self) -> None:
        if self._search_matches:
            self._search_idx = (self._search_idx - 1) % len(self._search_matches)
            self._jump_to_match()

    def _jump_to_match(self) -> None:
        if not self._search_matches:
            return
        table = self.query_one("#bond-table", DataTable)
        table.move_cursor(row=self._search_matches[self._search_idx])

    def action_override_px(self) -> None:
        """Stub: real implementation would open an input dialog."""
        self._set_status("Price override: not yet implemented — will open input dialog")

    def action_reset_override(self) -> None:
        table = self.query_one("#bond-table", DataTable)
        row_key = table.cursor_row
        if 0 <= row_key < len(self._filtered_rows):
            isin = self._filtered_rows[row_key].isin
            self._engine.clear_override(isin)
            self._do_refresh()
            self._set_status(f"Override cleared for {isin}")

    def _switch_tab(self, idx: int) -> None:
        self._current_tab_idx = idx % len(self._tabs)
        self._do_refresh()

    def action_tab_1(self) -> None: self._switch_tab(0)
    def action_tab_2(self) -> None: self._switch_tab(1)
    def action_tab_3(self) -> None: self._switch_tab(2)
    def action_tab_4(self) -> None: self._switch_tab(3)

    # ------------------------------------------------------------------
    # Search input handling
    # ------------------------------------------------------------------

    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        self._search_query = event.value.strip()
        bar = self.query_one("#search-bar", Container)
        bar.remove_class("visible")
        self.query_one("#bond-table", DataTable).focus()

        self._apply_tab_filter()
        self._populate_table()

        # Build match index for n/N navigation
        q = self._search_query.lower()
        self._search_matches = [
            i for i, r in enumerate(self._filtered_rows)
            if q in r.short_name.lower() or q in r.isin.lower()
        ]
        self._search_idx = 0
        self._jump_to_match()
        self._set_status(f"Search: '{self._search_query}' — {len(self._search_matches)} matches  [n/N to navigate]")
