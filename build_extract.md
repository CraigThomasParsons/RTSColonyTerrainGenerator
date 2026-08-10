# Stargus Local Build + Data Extract

This project expects Stargus at `/home/craigpar/Code/stargus` and Stratagus at
`/home/craigpar/Code/stratagus`.

## 1) Build Stratagus (CMake)

```
cd /home/craigpar/Code/stratagus
cmake -S . -B build -DLUA_LIBRARY=/usr/lib/liblua5.1.so -DLUA_INCLUDE_DIR=/usr/include/lua5.1
cmake --build build
```

## 2) Build Stargus (CMake)

Stargus needs StormLib. The system package was unusable here, so StormLib was
built from source at `/home/craigpar/Code/StormLib` and linked explicitly.

```
cd /home/craigpar/Code/StormLib
cmake -S . -B build
cmake --build build

cd /home/craigpar/Code/stargus
cmake -S . -B build \
  -DSTORMLIB_LIBRARY=/home/craigpar/Code/StormLib/build/libstorm.a \
  -DSTORMLIB_INCLUDE_DIR=/home/craigpar/Code/StormLib/src
cmake --build build
```

## 3) Extract StarCraft Data

MPQs found on this machine:

- `~/.wine/drive_c/Starcraft/StarDat.mpq`
- `~/.wine/drive_c/Starcraft/BrooDat.mpq`

Run `startool` from Stargus build output to extract data into a Stargus data dir.
You can choose either `~/.stratagus/sc` or `~/.local/share/stratagus/sc`.

Example (Wine install):

```
cd /home/craigpar/Code/stargus
./build/startool -v -s ~/.wine/drive_c/Starcraft ~/.stratagus/sc
```

### 3a) Extract MPQs from ISOs (no Wine)

If MPQs aren’t available in Wine, you can carve them directly from the CD
installers (ISOs in `/home/craigpar/StarcraftCds/`). The MPQ is embedded at a
known offset inside `INSTALL.EXE`.

```
mkdir -p /tmp/sc_iso_extract /tmp/bw_iso_extract /tmp/sc_mpq_dir

# Extract StarCraft INSTALL.EXE from the ISO and carve the embedded MPQ.
7z x /home/craigpar/StarcraftCds/STARCRAFT.ISO INSTALL.EXE -o/tmp/sc_iso_extract
python - <<'PY'
path='/tmp/sc_iso_extract/INSTALL.EXE'
off=0x3f600
size=601130098
out='/tmp/sc_iso_extract/STARCRAFT_INSTALL.MPQ'
with open(path,'rb') as f:
    f.seek(off)
    data=f.read(size)
with open(out,'wb') as w:
    w.write(data)
print('wrote', out, 'bytes', len(data))
PY

# Extract Brood War INSTALL.EXE from the ISO and carve the embedded MPQ.
7z x /home/craigpar/StarcraftCds/BROODWAR.ISO INSTALL.EXE -o/tmp/bw_iso_extract
python - <<'PY'
path='/tmp/bw_iso_extract/INSTALL.EXE'
off=0x40a00
size=566014469
out='/tmp/bw_iso_extract/BROODWAR_INSTALL.MPQ'
with open(path,'rb') as f:
    f.seek(off)
    data=f.read(size)
with open(out,'wb') as w:
    w.write(data)
print('wrote', out, 'bytes', len(data))
PY

# Use the carved MPQs for startool. StarCraft MPQ supplies the base data;
# BrooDat is provided as a fallback sub-archive.
cp -f /tmp/sc_iso_extract/STARCRAFT_INSTALL.MPQ /tmp/sc_mpq_dir/StarCraft.mpq
cp -f /tmp/bw_iso_extract/BROODWAR_INSTALL.MPQ /tmp/sc_mpq_dir/BrooDat.mpq

cd /home/craigpar/Code/stargus
./build/startool -v -s /tmp/sc_mpq_dir ~/.stratagus/sc
```

On first launch, Stargus will also prompt for StarCraft data location if data
was not already extracted.

## 4) Run Stargus

```
cd /home/craigpar/Code/stargus
./build/stargus
```

### Troubleshooting: Missing Sounds or Music

If you see errors about missing `music/title.ogg` or sounds like
`terran/.../*.ogg`, the extractor likely wrote audio under `sounds/`.
Create symlinks so the engine can find them:

```
ln -sfn ~/.stratagus/sc/sounds/terran ~/.stratagus/sc/terran
ln -sfn ~/.stratagus/sc/sounds/zerg ~/.stratagus/sc/zerg
ln -sfn ~/.stratagus/sc/sounds/protoss ~/.stratagus/sc/protoss
ln -sfn ~/.stratagus/sc/sounds/ui ~/.stratagus/sc/ui
ln -sfn ~/.stratagus/sc/sounds/misc ~/.stratagus/sc/misc
ln -sfn ~/.stratagus/sc/sounds/music ~/.stratagus/sc/music
```

Generated `.scm` files from the pipeline are copied into a `maps/` folder under
one of these data roots:

- `~/.stratagus/sc/maps`
- `~/.stratagus/stargus/maps`
- `~/.local/share/stratagus/sc/maps`
- `~/.local/share/stratagus/stargus/maps`

Override with `STARGUS_MAPS_DIR=/path/to/maps` when running
`MapGenerator/StargusExport/bin/consume_stargusexport_job.sh`.

For convenience, you can run the wrapper:

```
MapGenerator/run_stargus_export.sh
```

It defaults to copying into `~/.stratagus/sc/maps` unless you override
`STARGUS_MAPS_DIR`.
