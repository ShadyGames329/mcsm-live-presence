-- Exercise probe behavior with a fake engine and in-memory output only.
local output, worker, menu = "", nil, {}
local gameCalls = 0
local diagnostics = {}
local project, chapter, scene, script = "Minecraft101", "101_chapter1", "ForestTreehouse", "ForestTreehouse"
local env = setmetatable({}, {__index = _G})
env._G = env
env.io = {open = function(path)
    local parts = {}
    return {
        write = function(self, ...)
            for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
        end,
        close = function()
            if path:find('menu-observer-', 1, true) then
                diagnostics[#diagnostics + 1] = table.concat(parts)
            else
                output = table.concat(parts)
            end
        end,
    }
end}
env.RichPresence_Set = function() gameCalls = gameCalls + 1; return 1, nil, 3 end
env.Menu_Show = function() return 7, nil, 9 end
env.RichPresence_RestoreLogic = function() return nil, 5 end
env.Menu_GetCurrentMenu = function() return menu end
env.SubProject_GetCurrent = function() return project end
env.SaveLoad_GetChapterID = function() return chapter end
env.Game_GetScene = function() return scene end
env.Game_GetCurrentScript = function() return script end
env.Sleep = function() coroutine.yield() end
env.ThreadStart = function(fn)
    worker = coroutine.create(fn)
    assert(coroutine.resume(worker))
end
local function loadTemplate(path)
    local file = assert(io.open(path, "rb"))
    local source = file:read("*a"); file:close()
    source = source:gsub("__TELEMETRY_PATH__", '"mock/live-state.txt"')
    source = source:gsub("__OBSERVER_LOG_PATH__", '"mock/menu-observer-v3.txt"')
    source = source:gsub("__DIAGNOSTICS_ENABLED__", "true")
    return assert(load(source, "@" .. path, "t", env))()
end
loadTemplate("src/mcsm_live_presence/lua/live_probe.lua")
local a, b, c = env.RichPresence_Set("richPresence_mainMenu")
assert(a == 1 and b == nil and c == 3, "original return values changed")
assert(output:find("mode=menu\n", 1, true))
menu.isEpisodeSelect = true
assert(coroutine.resume(worker))
assert(output:find("mode=browsing\n", 1, true), "browser change missed without presence event")
menu.isEpisodeSelect = false
assert(coroutine.resume(worker))
assert(output:find("mode=menu\n", 1, true))
-- The current-menu getter does not expose the episode template flag.
env.Menu_GetCurrentMenu = function() return {} end
local beforeCalls = gameCalls
-- Reproduce V2C's evidence: actual objects lack the template flag. Only the
-- constructor's private instance marker should identify the episode browser.
loadTemplate("src/mcsm_live_presence/lua/menu_observer.lua")
env.MCSM_MenuObserved({__MCSM_episodeBrowser = true})
assert(output:find('mode=browsing\n', 1, true))
assert(table.concat(diagnostics):find('private=true template=nil', 1, true))
env.MCSM_MenuObserved({})
assert(output:find('mode=menu\n', 1, true))
assert(gameCalls == beforeCalls)
env.RichPresence_Set("richPresence_episode1")
assert(output:find("episode=1\n", 1, true))
assert(output:find("chapter=101_chapter1\n", 1, true))
assert(output:find("scene=ForestTreehouse\n", 1, true))
scene, script, chapter = "ForestStage", "ForestStage", "101_chapter2"
assert(coroutine.resume(worker))
assert(output:find("scene=ForestStage\n", 1, true), "scene change missed without save/presence event")
assert(output:find("chapter=101_chapter2\n", 1, true))
env.SaveLoad_GetChapterID = function() error("getter unavailable") end
scene = {}
assert(coroutine.resume(worker))
assert(output:find("chapter=\n", 1, true), "missing chapter should be omitted")
assert(output:find("scene=ForestStage\n", 1, true))
assert(output:find("metadata_source=live_script\n", 1, true))
env.RichPresence_Set("richPresence_pauseMenu")
assert(output:find("mode=paused\n", 1, true))
local x, y = env.RichPresence_RestoreLogic()
assert(x == nil and y == 5)
assert(output:find("mode=gameplay\n", 1, true))
env.RichPresence_Set("richPresence_mainMenu")
assert(output:find("episode=\n", 1, true), "gameplay metadata leaked into menu")
print("Probe mock checks passed: browser, live metadata, pause/resume, original returns.")
