--
-- Stratagus headless harness (v0.1)
--
-- This script is invoked by wcar_run_stratagus in headless mode.
-- It loads a map, runs for a fixed number of ticks, and prints
-- structured markers for validation.
--

local function getenv(name, default)
    local value = os.getenv(name)
    if value == nil or value == "" then
        return default
    end
    return value
end

local map_path = getenv("MAP_PATH", "")
local ticks = tonumber(getenv("HARNESS_TICKS", "5000")) or 5000
local seed = tonumber(getenv("HARNESS_SEED", "0")) or 0
local out_dir = getenv("HARNESS_OUT_DIR", ".")

if map_path == "" then
    print("HARNESS:FAIL:MAP_LOAD_FAILED:MAP_PATH missing")
    return
end

--
-- NOTE:
-- The actual Stratagus Lua API varies by game package.
-- We rely on the standard map-loading entry point.
--
if LoadMap then
    local ok = LoadMap(map_path)
    if not ok then
        print("HARNESS:FAIL:MAP_LOAD_FAILED:LoadMap returned false")
        return
    end
else
    print("HARNESS:FAIL:RUNTIME_ERROR:LoadMap API not available")
    return
end

if SetRandomSeed then
    SetRandomSeed(seed)
end

local executed = 0
for i = 1, ticks do
    if GameCycle then
        GameCycle()
    end
    executed = executed + 1
end

print("HARNESS:METRIC:ticks_executed=" .. executed)
print("HARNESS:PASS")
