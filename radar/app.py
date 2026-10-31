"""Radar Okazji – wyszukiwarka ofert pojazdów (GUI Tkinter)."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, ttk
from typing import List, Optional

import engine
import notifier
import storage
from models import DEFAULT_EXCLUDED, Listing, SearchParams


def _opt_int(text: str) -> Optional[int]:
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Radar Okazji – pojazdy")
        self.geometry("1050x720")
        self.minsize(900, 600)
        self.msgs: "queue.Queue[tuple]" = queue.Queue()
        self.results: List[Listing] = []
        self.busy = False
        self.auto_job: Optional[str] = None
        self.vars = {k: tk.StringVar() for k in (
            "brand", "model", "year_from", "year_to", "price_from",
            "price_to", "my_location", "max_distance", "keywords",
            "excluded", "webhook", "interval")}
        self.use_otomoto = tk.BooleanVar(value=True)
        self.use_olx = tk.BooleanVar(value=True)
        self.notify = tk.BooleanVar(value=False)
        self.auto = tk.BooleanVar(value=False)
        self._build()
        self._load()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(150, self._poll)

    # ---------------------------------------------------------------- UI
    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Kryteria wyszukiwania", padding=8)
        form.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(form, text="Cel wyszukiwania:").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="pojazd", font=("", 10, "bold")).grid(
            row=0, column=1, sticky="w")

        def field(row, col, label, key, width=18):
            ttk.Label(form, text=label).grid(row=row, column=col, sticky="w",
                                             padx=(0, 4), pady=3)
            ttk.Entry(form, textvariable=self.vars[key], width=width).grid(
                row=row, column=col + 1, sticky="we", padx=(0, 14))

        field(1, 0, "Marka:", "brand")
        field(1, 2, "Model:", "model")
        field(2, 0, "Rok od:", "year_from", 8)
        field(2, 2, "Rok do:", "year_to", 8)
        field(3, 0, "Cena od (zł):", "price_from", 10)
        field(3, 2, "Cena do (zł):", "price_to", 10)
        field(4, 0, "Moja lokalizacja:", "my_location")
        field(4, 2, "Maks. odległość (km):", "max_distance", 8)
        field(5, 0, "Opis zawiera (opcjonalnie):", "keywords", 30)
        field(5, 2, "Odrzuć, jeśli opis zawiera (opcjonalnie):", "excluded", 30)
        ttk.Button(form, text="Wstaw przykładowe frazy do odrzucania",
                   command=lambda: self.vars["excluded"].set(DEFAULT_EXCLUDED)
                   ).grid(row=6, column=2, columnspan=2, sticky="e")
        ttk.Label(form, text="(lokalizacja: wpisz miasto – program policzy "
                  "odległość do każdej oferty)", foreground="#666").grid(
            row=6, column=0, columnspan=2, sticky="w")
        src = ttk.Frame(form)
        src.grid(row=0, column=2, columnspan=2, sticky="e")
        ttk.Checkbutton(src, text="Otomoto", variable=self.use_otomoto).pack(
            side="left", padx=4)
        ttk.Checkbutton(src, text="OLX", variable=self.use_olx).pack(side="left")

        dc = ttk.LabelFrame(self, text="Powiadomienia Discord", padding=8)
        dc.pack(fill="x", padx=10, pady=4)
        ttk.Label(dc, text="Webhook URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(dc, textvariable=self.vars["webhook"], show="•").grid(
            row=0, column=1, sticky="we", padx=6)
        ttk.Button(dc, text="Wyślij test", command=self._test_webhook).grid(
            row=0, column=2)
        ttk.Checkbutton(dc, text="Powiadamiaj o nowych ofertach (@everyone)",
                        variable=self.notify).grid(row=1, column=0,
                                                   columnspan=2, sticky="w")
        auto = ttk.Frame(dc)
        auto.grid(row=1, column=2, sticky="e")
        ttk.Checkbutton(auto, text="Szukaj automatycznie co",
                        variable=self.auto, command=self._toggle_auto).pack(
            side="left")
        ttk.Entry(auto, textvariable=self.vars["interval"], width=4).pack(
            side="left", padx=3)
        ttk.Label(auto, text="min").pack(side="left")
        dc.columnconfigure(1, weight=1)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=4)
        self.btn = ttk.Button(bar, text="🔍  SZUKAJ", command=self.start_search)
        self.btn.pack(side="left")
        self.status = ttk.Label(bar, text="Gotowy.")
        self.status.pack(side="left", padx=12)

        cols = ("title", "price", "year", "km", "loc", "dist", "src")
        heads = ("Tytuł", "Cena", "Rok", "Przebieg", "Lokalizacja",
                 "Odległość", "Źródło")
        widths = (330, 90, 55, 85, 190, 80, 70)
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree.bind("<Double-1>", self._open)
        ttk.Label(self, text="Dwuklik na ofercie otwiera ogłoszenie.",
                  foreground="#666").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(self, height=6, state="disabled")
        self.log.pack(fill="x", padx=10, pady=(4, 10))

    # ------------------------------------------------------ ustawienia
    def _load(self) -> None:
        s = storage.load_settings()
        defaults = {"interval": "15"}
        for k, var in self.vars.items():
            var.set(str(s.get(k, defaults.get(k, "")) or ""))
        self.use_otomoto.set(s.get("use_otomoto", True))
        self.use_olx.set(s.get("use_olx", True))
        self.notify.set(s.get("notify", False))

    def _save(self) -> None:
        data = {k: v.get() for k, v in self.vars.items()}
        data.update(use_otomoto=self.use_otomoto.get(),
                    use_olx=self.use_olx.get(), notify=self.notify.get())
        storage.save_settings(data)

    def _params(self) -> SearchParams:
        v = {k: x.get().strip() for k, x in self.vars.items()}
        return SearchParams(
            brand=v["brand"], model=v["model"],
            year_from=_opt_int(v["year_from"]), year_to=_opt_int(v["year_to"]),
            price_from=_opt_int(v["price_from"]),
            price_to=_opt_int(v["price_to"]), my_location=v["my_location"],
            max_distance_km=_opt_int(v["max_distance"]),
            description_keywords=v["keywords"], excluded_phrases=v["excluded"],
            use_otomoto=self.use_otomoto.get(), use_olx=self.use_olx.get())

    # ---------------------------------------------------------- akcje
    def _log(self, text: str) -> None:
        self.msgs.put(("log", text))

    def start_search(self) -> None:
        if self.busy:
            return
        params = self._params()
        if not (params.use_otomoto or params.use_olx):
            messagebox.showwarning("Radar", "Wybierz co najmniej jedno źródło.")
            return
        self._save()
        self.busy = True
        self.btn.state(["disabled"])
        self.status.config(text="Szukam…")
        threading.Thread(target=self._worker, args=(params,),
                         daemon=True).start()

    def _worker(self, params: SearchParams) -> None:
        try:
            results = engine.run_search(params, self._log)
            if self.notify.get() and self.vars["webhook"].get().strip():
                for item in results:
                    if storage.is_new(item.uid):
                        try:
                            notifier.send_discord(
                                self.vars["webhook"].get(),
                                notifier.format_message(params, item))
                            storage.mark_seen(item.uid)
                            self._log(f"Discord: wysłano „{item.title}”.")
                        except Exception as exc:  # noqa: BLE001
                            self._log(f"Discord – błąd: {exc}")
                            break
            else:
                for item in results:
                    storage.mark_seen(item.uid)
            self.msgs.put(("results", results))
        except Exception as exc:  # noqa: BLE001
            self.msgs.put(("log", f"Błąd: {exc}"))
            self.msgs.put(("results", []))

    def _test_webhook(self) -> None:
        url = self.vars["webhook"].get().strip()
        if not url:
            messagebox.showinfo("Radar", "Wklej najpierw adres webhooka.")
            return
        try:
            notifier.send_discord(url, notifier.format_message(
                self._params(), None).replace("Nowa oferta", "Test połączenia"))
            messagebox.showinfo("Radar", "Wysłano wiadomość testową.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Radar", f"Nie udało się wysłać:\n{exc}")

    def _toggle_auto(self) -> None:
        if self.auto_job:
            self.after_cancel(self.auto_job)
            self.auto_job = None
        if self.auto.get():
            self._schedule()
            self.start_search()

    def _schedule(self) -> None:
        minutes = max(1, _opt_int(self.vars["interval"].get()) or 15)
        self.auto_job = self.after(minutes * 60_000, self._auto_tick)

    def _auto_tick(self) -> None:
        if self.auto.get():
            self.start_search()
            self._schedule()

    def _open(self, _event) -> None:
        sel = self.tree.selection()
        if sel:
            webbrowser.open(self.results[int(sel[0])].url)

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.msgs.get_nowait()
                if kind == "log":
                    self.log.config(state="normal")
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    self.log.config(state="disabled")
                else:
                    self._show(payload)
        except queue.Empty:
            pass
        self.after(150, self._poll)

    def _show(self, results: List[Listing]) -> None:
        self.results = results
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(results):
            self.tree.insert("", "end", iid=str(i), values=(
                r.title, f"{r.price:,} zł".replace(",", " ") if r.price else "—",
                r.year or "—", f"{r.mileage:,} km".replace(",", " ")
                if r.mileage else "—", r.location or "—",
                f"{r.distance_km:.0f} km" if r.distance_km is not None else "—",
                r.source))
        self.busy = False
        self.btn.state(["!disabled"])
        self.status.config(text=f"Znaleziono: {len(results)}")

    def _close(self) -> None:
        self._save()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
