-- Menu_Show passes the actual instance, tagged by the episode constructor.
local env, globals = _ENV, _G
local path = __OBSERVER_LOG_PATH__
local sequence = 0
local function log(message)
    if not __DIAGNOSTICS_ENABLED__ then return end
    pcall(function()
        if type(io) ~= "table" or type(io.open) ~= "function" then return end
        local file = io.open(path, "ab")
        if file then file:write(message, "\n"); file:close() end
    end)
end
local function observed(menu)
    sequence = sequence + 1
    local ok, marked, template = pcall(function()
        return menu.__MCSM_episodeBrowser == true, menu.isEpisodeSelect
    end)
    local notify = env.RichPresence_Set
    if type(notify) ~= "function" and type(globals) == "table" then notify = globals.RichPresence_Set end
    log("show=" .. tostring(sequence) .. " type=" .. type(menu)
        .. " private=" .. tostring(marked) .. " template=" .. tostring(template)
        .. " notify=" .. type(notify))
    if ok and type(notify) == "function" then
        local marker = marked and "__MCSM_EPISODE_BROWSER_SHOWN" or "__MCSM_OTHER_MENU_SHOWN"
        local sent = pcall(notify, marker)
        log("delivered=" .. tostring(sent))
    end
end
env.MCSM_MenuObserved = observed
if type(globals) == "table" then globals.MCSM_MenuObserved = observed end
log("module_loaded=1 private_marker_version=3")
