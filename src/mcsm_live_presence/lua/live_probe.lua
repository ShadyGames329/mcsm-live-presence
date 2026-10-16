-- Local live-state experiment. No saves or game resources are written.
-- Source is Lua 5.2 compatible and packaged as an encrypted source module.
local env = _G
if type(env) ~= "table" or env.MCSM_LIVE_PROBE_V2 then return end
env.MCSM_LIVE_PROBE_V2 = true
local destination = __TELEMETRY_PATH__
local baseMode, presenceKey = "unknown", "probe_initialized"
local browserShown = nil
local counter, previous = 0, ""
local unpackValues = table.unpack or unpack
local function pack(...) return { n = select("#", ...), ... } end

local function call(name, ...)
    local fn = env[name]
    if type(fn) ~= "function" then return nil end
    local ok, value = pcall(fn, ...)
    if ok then return value end
end

local function text(value)
    if type(value) ~= "string" then return "" end
    if #value > 160 or value:find("[\r\n=]") then return "" end
    return value
end

local function sample()
    local mode = baseMode
    local current = call("Menu_GetCurrentMenu")
    if mode == "menu" and (browserShown == true or
        (browserShown == nil and type(current) == "table" and current.isEpisodeSelect == true)) then
        mode = "browsing"
    end
    local episode, chapter, scene, script, source = "", "", "", "", ""
    if mode == "gameplay" or mode == "paused" then
        local project = text(call("SubProject_GetCurrent"))
        episode = project:match("^Minecraft10([1-8])$") or ""
        if episode == "" then
            local number = call("SubProject_GetEpisodeNumber")
            if type(number) == "number" and number >= 1 and number <= 8 and number % 1 == 0 then
                episode = tostring(number)
            end
        end
        local value = call("SaveLoad_GetChapterID")
        if type(value) == "number" and value >= 1 and value <= 20 and value % 1 == 0 then
            chapter = tostring(value)
        else
            chapter = text(value)
        end
        scene = text(call("Game_GetScene"))
        script = text(call("Game_GetCurrentScript"))
        if scene ~= "" then source = "live_scene" end
        if scene == "" and script ~= "" then
            scene, source = script, "live_script"
        end
    end
    local body = "mode=" .. mode .. "\npresence_key=" .. presenceKey
        .. "\nepisode=" .. episode .. "\nchapter=" .. chapter
        .. "\nscene=" .. scene .. "\nscript=" .. script
        .. "\nmetadata_source=" .. source .. "\n"
    if body == previous then return end
    if type(io) ~= "table" or type(io.open) ~= "function" then return end
    local file = io.open(destination, "wb")
    if not file then return end
    counter = counter + 1
    file:write("format=2\n", body, "event_count=", tostring(counter), "\n")
    file:close()
    previous = body
end

local function publish() pcall(sample) end
local originalSet = env.RichPresence_Set
if type(originalSet) == "function" and type(unpackValues) == "function" then
    env.RichPresence_Set = function(key, ...)
        -- Private observer messages are consumed here, never sent to the game.
        if key == "__MCSM_EPISODE_BROWSER_SHOWN" or key == "__MCSM_OTHER_MENU_SHOWN" then
            browserShown = key == "__MCSM_EPISODE_BROWSER_SHOWN"
            publish()
            return
        end
        local result = pack(originalSet(key, ...))
        presenceKey = text(key)
        if key == "richPresence_mainMenu" then baseMode = "menu"
        elseif key == "richPresence_pauseMenu" then baseMode = "paused"
        elseif type(key) == "string" and key:find("richPresence_episode", 1, true) == 1 then
            baseMode = "gameplay"
        end
        publish()
        return unpackValues(result, 1, result.n)
    end
end

local originalRestore = env.RichPresence_RestoreLogic
if type(originalRestore) == "function" and type(unpackValues) == "function" then
    env.RichPresence_RestoreLogic = function(...)
        local result = pack(originalRestore(...))
        if baseMode == "paused" then
            baseMode, presenceKey = "gameplay", "restored_from_pause"
        end
        publish()
        return unpackValues(result, 1, result.n)
    end
end

publish()
-- Sampling also observes scene/chapter changes without waiting for a save or a
-- new presence event. Missing thread APIs leave event-based reporting available.
if type(env.ThreadStart) == "function" and type(env.Sleep) == "function" then
    pcall(env.ThreadStart, function()
        while true do
            env.Sleep(0.5)
            publish()
        end
    end)
end
