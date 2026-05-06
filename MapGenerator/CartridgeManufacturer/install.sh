#!/usr/bin/env bash
set -e

MODULE_ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$MODULE_ROOT/bin/wcar-tools"
cargo build --release

cp target/release/wcar_pack "$MODULE_ROOT/wcar_pack"
cp target/release/wcar_export_chk "$MODULE_ROOT/wcar_export_chk"
cp target/release/wcar_run_stratagus "$MODULE_ROOT/wcar_run_stratagus"

chmod +x "$MODULE_ROOT/wcar_pack"
chmod +x "$MODULE_ROOT/wcar_export_chk"
chmod +x "$MODULE_ROOT/wcar_run_stratagus"

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

ln -sf "$MODULE_ROOT/systemd/cartridge.service" "$SYSTEMD_USER_DIR/cartridge.service"
ln -sf "$MODULE_ROOT/systemd/cartridge.path" "$SYSTEMD_USER_DIR/cartridge.path"

systemctl --user daemon-reload
systemctl --user enable --now cartridge.path

echo "Installed CartridgeManufacturer tools and systemd units."
