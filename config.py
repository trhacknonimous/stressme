from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

ALLOWED_HOSTS = {
    item.strip().lower().rstrip(".")
    for item in os.getenv("ALLOWED_HOSTS", "").split(",")
    if item.strip()
}
PASSWORD = os.getenv("STRESSLAB_PASSWORD", "")
MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "500"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "5"))
MIN_INTERVAL_MS = int(os.getenv("MIN_INTERVAL_MS", "500"))
MAX_K6_VUS = int(os.getenv("MAX_K6_VUS", "5"))
MAX_K6_DURATION = int(os.getenv("MAX_K6_DURATION", "30"))
MAX_K6_RATE = int(os.getenv("MAX_K6_RATE", "5"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/stresslab.sqlite3")
K6_BIN = os.getenv("K6_BIN", "/usr/bin/k6")


def validate_target(url: str) -> str:
    """Validate an HTTPS URL against exact allowed hostnames and public DNS."""
    if not url or len(url) > 2048:
        raise ValueError("URL vide ou trop longue.")

    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("Seules les URL HTTPS sont autorisées.")
    if not parsed.hostname:
        raise ValueError("Nom d'hôte manquant.")
    if parsed.username or parsed.password:
        raise ValueError("Identifiants dans l'URL interdits.")
    if parsed.port not in (None, 443):
        raise ValueError("Seul le port HTTPS standard (443) est autorisé.")
    if parsed.fragment:
        raise ValueError("Les fragments URL ne sont pas acceptés.")

    host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise ValueError("Domaine absent de la liste blanche.")

    try:
        ip = ipaddress.ip_address(host)
        addresses = {ip}
    except ValueError:
        try:
            records = socket.getaddrinfo(
                host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
            addresses = {ipaddress.ip_address(record[4][0]) for record in records}
        except socket.gaierror as exc:
            raise ValueError("Résolution DNS impossible.") from exc

    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("La cible résout vers une adresse IP non publique.")

    # Strip fragment, normalize scheme/hostname, preserve path and query.
    netloc = host
    path = parsed.path or "/"
    return urlunsplit(("https", netloc, path, parsed.query, ""))
