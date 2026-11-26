# TRHACKNON WEB STRESS LAB

Application Streamlit pour des tests HTTP bornés sur des domaines explicitement autorisés. Moteurs : Python asyncio/httpx et k6. Historique SQLite.

## Prérequis

- Kali/Debian récent
- Python 3.10+
- k6 installé depuis le dépôt officiel
- Un domaine HTTPS que vous administrez et avez autorisation de tester

## Installation

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl ca-certificates gnupg
sudo mkdir -p /opt/trhacknon-stresslab
sudo chown -R "$USER":"$USER" /opt/trhacknon-stresslab
```

Extraire l'archive dans `/opt/trhacknon-stresslab`, puis :

```bash
cd /opt/trhacknon-stresslab
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
openssl rand -hex 32
nano .env
chmod 600 .env
```

Dans `.env`, définir `STRESSLAB_PASSWORD` et `ALLOWED_HOSTS` avec les noms exacts de vos domaines. Les domaines sont exacts, sans wildcard.

### Installer k6

```bash
sudo install -d /etc/apt/keyrings
curl -fsSL https://dl.k6.io/key.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/k6-archive-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt update
sudo apt install -y k6
k6 version
```

## Vérifier et lancer

```bash
python -m py_compile config.py storage.py app.py engine/*.py
streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Depuis votre poste, ouvrir un tunnel SSH (adapter l'utilisateur, l'hôte et le port SSH) :

```bash
ssh -p 3393 -L 8501:127.0.0.1:8501 utilisateur@IP_DU_VPS
```

Puis ouvrir `http://127.0.0.1:8501`.

## Service systemd

Le fichier `systemd/trhacknon-stresslab.service` suppose que le projet est installé dans `/opt/trhacknon-stresslab` et que l'utilisateur système s'appelle `trhacknon`. Ajuster `User=` si nécessaire.

```bash
sudo cp systemd/trhacknon-stresslab.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trhacknon-stresslab
sudo systemctl status trhacknon-stresslab
sudo journalctl -u trhacknon-stresslab -f
```

## Sécurité et limites

- HTTPS uniquement, port 443 uniquement.
- Liste blanche de noms d'hôtes exacts.
- Contrôle DNS initial : les adresses privées/non globales sont rejetées.
- Pas de redirections HTTP suivies.
- Pas de proxy d'environnement.
- Limites strictes configurables pour nombre, concurrence, débit, durée et VUs.
- Garder Streamlit lié à `127.0.0.1` et accéder par tunnel SSH ou VPN.
- Utiliser uniquement sur des systèmes dont vous êtes propriétaire ou pour lesquels vous avez une autorisation explicite.

**Important :** la validation DNS applicative n'élimine pas à elle seule les risques de rebinding DNS/TOCTOU. Pour une utilisation exposée ou multi-utilisateur, ajouter un filtrage egress au niveau pare-feu/réseau et une politique de sortie stricte. Ne pas exposer directement ce dashboard à Internet sans reverse proxy TLS, protections d'accès et durcissement complémentaire.

Tor n'est pas utilisé pour les campagnes. Cette application est un outil de mesure de performance contrôlé, pas un mécanisme d'anonymisation ou de contournement de protections.
# stressme
