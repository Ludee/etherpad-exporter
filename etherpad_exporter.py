"""
Etherpad Exporter
Lädt Etherpad-Dokumente in verschiedenen Formaten herunter und speichert sie lokal.
"""

import requests
from pathlib import Path
from urllib.parse import urlparse


class EtherpadExporter:
    """Exportiert Etherpads in verschiedenen Formaten."""

    EXPORT_FORMATS = ["etherpad", "html", "txt"]

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

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; EtherpadExporter/1.0)"
    }

    def _download(self, url: str) -> bytes | None:
        """Lädt eine URL herunter. Gibt None bei Fehler zurück."""
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            print(f"  ✗ Fehler beim Abrufen von {url}: {e}")
            return None

    def export_pad(self, pad_url: str) -> dict[str, bool]:
        """
        Exportiert ein einzelnes Pad in allen konfigurierten Formaten.
        Gibt ein Dict zurück: {format: success}
        """
        pad_name = self._pad_name(pad_url)
        print(f"Exportiere: {pad_name}")
        results = {}

        for fmt in self.formats:
            export_url = self._export_url(pad_url, fmt)
            content = self._download(export_url)

            if content is not None:
                file_path = self.output_dir / f"{pad_name}.{fmt}"
                file_path.write_bytes(content)
                print(f"  ✓ {fmt:10} → {file_path}")
                results[fmt] = True
            else:
                results[fmt] = False

        return results

    def export_all(self, pad_urls: list[str]) -> None:
        """Exportiert eine Liste von Pad-URLs."""
        total = len(pad_urls)
        success_count = 0

        for i, url in enumerate(pad_urls, 1):
            print(f"\n[{i}/{total}]", end=" ")
            results = self.export_pad(url)
            if any(results.values()):
                success_count += 1

        print(f"\n✓ Fertig: {success_count}/{total} Pads erfolgreich exportiert.")
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
