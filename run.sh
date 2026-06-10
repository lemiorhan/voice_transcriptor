#!/usr/bin/env bash
#
# Tek komutla çalıştır: sanal ortamı kurar, bağımlılıkları (gerekiyorsa) yükler
# ve uygulamayı başlatır.
#
#   ./run.sh
#
# Ortam değişkenleri (opsiyonel):
#   PYTHON=python3.11 ./run.sh   # kullanılacak Python yorumlayıcısı

set -euo pipefail

# Script'in bulunduğu dizine geç (her yerden çalıştırılabilsin).
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV=".venv"
REQ="requirements.txt"
STAMP="$VENV/.requirements.sha"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Hata: '$PYTHON' bulunamadı. Python 3 kurun veya PYTHON=... ile belirtin." >&2
  exit 1
fi

# 1) Sanal ortam yoksa oluştur.
if [ ! -d "$VENV" ]; then
  echo "==> Sanal ortam oluşturuluyor ($VENV)..."
  "$PYTHON" -m venv "$VENV"
fi

VPY="$VENV/bin/python"

# 2) Bağımlılıkları yalnızca requirements.txt değiştiyse (veya ilk kez) yükle.
NEWSHA="$(shasum "$REQ" | awk '{print $1}')"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP" 2>/dev/null)" != "$NEWSHA" ]; then
  echo "==> Bağımlılıklar yükleniyor (ilk kurulum torch vb. büyük paketleri indirir, biraz sürebilir)..."
  "$VPY" -m pip install --upgrade pip
  "$VPY" -m pip install -r "$REQ"
  echo "$NEWSHA" > "$STAMP"
fi

# 3) Uygulamayı başlat (argümanları olduğu gibi geçir).
exec "$VPY" meeting-transcriptor.py "$@"
