# WorldFeatures Setup

## Prerequisites
- Java 17+ (or compatible JRE)
- Gradle available on PATH (or add a local `gradlew`)
- systemd user session

## Install
```sh
chmod +x install.sh
./install.sh
```

## Verify systemd
```sh
systemctl --user status worldfeatures.path --no-pager
```

## Manual run
```sh
bin/consume_worldfeatures_job.sh
```

Defaults:
- Input: `MapGenerator/TreePlanter/outbox`
- Output: `MapGenerator/WorldFeatures/outbox`
- Logs: `logs/jobs/<job_id>/worldfeatures.log`

Environment overrides:
- `WORLD_FEATURES_INPUT_DIR`
- `WORLD_FEATURES_OUTPUT_DIR`
- `WORLD_FEATURES_LOG_DIR`
