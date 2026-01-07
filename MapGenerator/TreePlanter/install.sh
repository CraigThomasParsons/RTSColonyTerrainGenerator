#!/usr/bin/env bash
#
# TreePlanter install script
#
# Responsibilities:
# - Download Composer locally (using php84)
# - Install vendor dependencies and autoloader
# - Install and enable systemd user units
#
# This script is safe to run multiple times.
#

set -euo pipefail

TREEPLANTER_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TreePlanter"

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

PHP_BIN="/usr/bin/php84"

echo "[TreePlanter] Starting installation..."

#
# -------------------------------------------------------------------
# Step 1: Ensure required directories exist
# -------------------------------------------------------------------
#

mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$TREEPLANTER_ROOT/bin"

#
# -------------------------------------------------------------------
# Step 2: Download Composer locally (if not present)
# -------------------------------------------------------------------
#

COMPOSER_BIN="$TREEPLANTER_ROOT/bin/composer"

if [[ ! -f "$COMPOSER_BIN" ]]; then
    echo "[TreePlanter] Downloading Composer..."

    cd "$TREEPLANTER_ROOT/bin"

    "$PHP_BIN" -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"

    "$PHP_BIN" composer-setup.php \
        --install-dir="$TREEPLANTER_ROOT/bin" \
        --filename=composer

    rm composer-setup.php
    chmod +x "$COMPOSER_BIN"
else
    echo "[TreePlanter] Composer already present, skipping download."
fi

#
# -------------------------------------------------------------------
# Step 3: Install vendor dependencies and autoloader
# -------------------------------------------------------------------
#

echo "[TreePlanter] Installing Composer dependencies..."

cd "$TREEPLANTER_ROOT"

"$COMPOSER_BIN" install \
    --no-interaction \
    --prefer-dist

#
# -------------------------------------------------------------------
# Step 4: Install systemd user units
# -------------------------------------------------------------------
#

echo "[TreePlanter] Installing systemd user units..."

ln -sf \
    "$TREEPLANTER_ROOT/systemd/treeplanter.service" \
    "$SYSTEMD_USER_DIR/treeplanter.service"

ln -sf \
    "$TREEPLANTER_ROOT/systemd/treeplanter.path" \
    "$SYSTEMD_USER_DIR/treeplanter.path"

#
# -------------------------------------------------------------------
# Step 5: Reload and enable systemd units
# -------------------------------------------------------------------
#

systemctl --user daemon-reload
systemctl --user enable --now treeplanter.path

echo "[TreePlanter] Installation complete."
