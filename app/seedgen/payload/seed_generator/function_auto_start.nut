// This file is installed only for a temporary seed-generation session.
// Use the engine's fully-shown callback and campaign entry point, never timers
// or UI clicks. All bootstrap work runs before the generator reseeds its RNG.
local S = ::SeedGenerator;
local cfg = S.CampaignConfig;
S.AutoStartAttempted <- false;
::logInfo("BBMODSeedSession: " + cfg.SessionID);

::mods_hookClass("states/main_menu_state", function(o)
{
    local onShown = o.main_menu_screen_onScreenShown;
    o.main_menu_screen_onScreenShown = function()
    {
        onShown();
        if (S.AutoStartAttempted) return;
        S.AutoStartAttempted = true;
        try
        {
            if (this.isScenarioDemo())
            {
                this.logError("BBMODSeedStart: error demo-unavailable");
                return;
            }
            local scenario = this.m.ScenarioManager.getScenario(cfg.Origin);
            if (scenario == null || !scenario.isValid())
            {
                this.logError("BBMODSeedStart: error origin-unavailable " + cfg.Origin);
                return;
            }
            if (this.Const.PlayerBanners.len() == 0)
            {
                this.logError("BBMODSeedStart: error banners-unavailable");
                return;
            }
            this.m.SelectedCampaignFileName = null;
            this.logInfo("BBMODSeedStart: requested " + cfg.Origin);
            this.campaign_menu_module_onStartPressed({
                Name = "BBMOD Seed Search",
                Banner = this.Const.PlayerBanners[0],
                Difficulty = cfg.Difficulty,
                EconomicDifficulty = cfg.EconomicDifficulty,
                BudgetDifficulty = cfg.BudgetDifficulty,
                Ironman = false,
                ExplorationMode = false,
                GreaterEvil = 0,
                PermanentDestruction = false,
                Seed = cfg.SessionID.len() >= 10 ? cfg.SessionID.slice(0, 10) : "BBMODSEEDS",
                StartingScenario = cfg.Origin
            });
        }
        catch (error)
        {
            this.logError("BBMODSeedStart: error start-failed " + error);
        }
    };
});

::mods_hookClass("states/world_state", function(o)
{
    local start = o.startNewCampaign;
    o.startNewCampaign = function()
    {
        local settings = this.m.CampaignSettings;
        if (settings == null || settings.StartingScenario == null ||
            settings.StartingScenario.getID() != cfg.Origin ||
            settings.Difficulty != cfg.Difficulty ||
            settings.EconomicDifficulty != cfg.EconomicDifficulty ||
            settings.BudgetDifficulty != cfg.BudgetDifficulty)
        {
            this.logError("BBMODSeedStart: error settings-mismatch");
            throw "BBMOD seed campaign settings mismatch";
        }
        this.logInfo("BBMODSeedStart: generating " + cfg.Origin);
        try { return start(); }
        catch (error)
        {
            this.logError("BBMODSeedStart: error generation-failed " + error);
            throw error;
        }
    };
});
