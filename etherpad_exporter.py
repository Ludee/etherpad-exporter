"""
Etherpad Exporter
Lädt Etherpad-Dokumente in verschiedenen Formaten herunter und speichert sie lokal.
"""

import time
import requests
from pathlib import Path
from urllib.parse import urlparse


class EtherpadExporter:
    """Exportiert Etherpads in verschiedenen Formaten."""

    EXPORT_FORMATS = ["etherpad", "html", "txt"]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; EtherpadExporter/1.0)"
    }
    TIMEOUT = 30
    RETRIES = 3
    RETRY_DELAY = 5  # Sekunden Pause vor jedem Retry-Durchlauf

    def __init__(self, output_dir: str = "pads", formats: list[str] = None):
        self.output_dir = Path(output_dir)
        self.formats = formats or self.EXPORT_FORMATS
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _pad_name(self, url: str) -> str:
        """Extrahiert den Pad-Namen aus der URL."""
        path = urlparse(url.rstrip("/")).path  # z.B. /p/htw-pv3-test
        return path.split("/p/")[-1]

    def _export_url(self, base_url: str, fmt: str) -> str:
        """Baut die Export-URL zusammen."""
        return f"{base_url.rstrip('/')}/export/{fmt}"

    def _download(self, url: str) -> bytes | None:
        """Lädt eine URL herunter. Gibt None bei Fehler zurück."""
        for attempt in range(1, self.RETRIES + 1):
            try:
                response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
                response.raise_for_status()
                return response.content
            except requests.Timeout:
                print(f"  ⏱ Timeout (Versuch {attempt}/{self.RETRIES}): {url}")
            except requests.RequestException as e:
                print(f"  ✗ Fehler beim Abrufen von {url}: {e}")
                return None  # Bei anderen Fehlern (z.B. 403) sofort abbrechen
        print(f"  ✗ Alle {self.RETRIES} Versuche fehlgeschlagen: {url}")
        return None

    def export_pad(self, pad_url: str) -> bool:
        """
        Exportiert ein einzelnes Pad in allen konfigurierten Formaten.
        Gibt True zurück wenn alle Formate erfolgreich waren, sonst False.
        """
        pad_name = self._pad_name(pad_url)
        print(f"Exportiere: {pad_name}")

        for fmt in self.formats:
            export_url = self._export_url(pad_url, fmt)
            content = self._download(export_url)

            if content is not None:
                file_path = self.output_dir / f"{pad_name}.{fmt}"
                file_path.write_bytes(content)
                print(f"  ✓ {fmt:10} → {file_path}")
            else:
                print(f"  ✗ {fmt:10} fehlgeschlagen – Pad wird wiederholt")
                return False  # Pad als Ganzes in die Retry-Queue

        return True

    def export_all(self, pad_urls: list[str]) -> None:
        """
        Exportiert alle Pads. Fehlgeschlagene werden in Folgedurchläufen
        wiederholt, bis alle erfolgreich exportiert wurden.
        """
        queue = list(pad_urls)
        total = len(queue)
        run = 1

        while queue:
            print(f"\n{'─' * 50}")
            print(f"Durchlauf {run} – {len(queue)}/{total} Pad(s) verbleibend")
            print(f"{'─' * 50}")

            failed = []
            for i, url in enumerate(queue, 1):
                print(f"\n[{i}/{len(queue)}]", end=" ")
                if not self.export_pad(url):
                    failed.append(url)

            queue = failed
            run += 1

            if queue:
                print(f"\n⚠ {len(queue)} Pad(s) fehlgeschlagen – neuer Versuch in {self.RETRY_DELAY}s ...")
                time.sleep(self.RETRY_DELAY)

        print(f"\n✓ Fertig: alle {total} Pads erfolgreich exportiert.")
        print(f"  Gespeichert in: {self.output_dir.resolve()}")


# ---------------------------------------------------------------------------
# Konfiguration & Ausführung
# ---------------------------------------------------------------------------

class PadListReader:
    """Liest Pad-URLs aus einer .txt-Datei (eine URL pro Zeile)."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def read(self) -> list[str]:
        """Gibt eine bereinigte Liste aller URLs zurück. Leere Zeilen und Kommentare (#) werden übersprungen."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {self.file_path}")

        urls = []
        for line in self.file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

        print(f"  {len(urls)} URLs geladen aus: {self.file_path}")
        return urls


if __name__ == "__main__":
    reader = PadListReader("pads.txt")       # Pfad zur URL-Liste
    pad_urls = reader.read()

    exporter = EtherpadExporter(
        output_dir="pads",                        # Zielordner
        formats=["etherpad", "html", "txt"],      # gewünschte Formate
    )
    exporter.export_all(pad_urls)
