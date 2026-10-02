// Custom origins use the real campaign entry point. Character creation, spawn,
// origin initialization and faction simulation retain vanilla's RNG ordering.
local S = ::SeedGenerator;
S.resetModCampaign <- function(state)
{
    ::Time.clearEvents();
    ::Root.setBackgroundTaskCallback(null);
    state.m.Player = null;
    state.m.Regions = [];
    state.m.LastPlayerTile = null;
    state.m.LastEnteredTown = null;
    state.m.LastEnteredLocation = null;
    state.m.AutoEnterLocation = null;
    state.m.AutoAttack = null;
    state.m.CombatStartTime = 0;
    ::World.getPlayerRoster().clear();
    foreach (manager in [::World.Combat, ::World.Events, ::World.Ambitions,
        ::World.Crafting, ::World.Retinue, ::World.Contracts, ::World.Statistics])
        manager.clear();
    ::World.Assets.m.Origin = null;
    ::World.Assets.clear();
    ::World.clearScene();
    ::World.EntityManager.clear();
    ::World.FactionManager.clear();
    // tag_collection has no clear() method. table.clear() would remove its
    // native set/get functions too, so create the same fresh object as onInit.
    state.m.Flags = ::new("scripts/tools/tag_collection");
    ::World.Flags = state.m.Flags;
    this.NamedIndex = 0;
    this.NamedIndexDict = {};
};

S.searchModOrigin <- function(state, nativeStart)
{
    local settings = clone state.m.CampaignSettings;
    if (settings.StartingScenario.getID() != "scenario.afeix_expedition")
        throw "Unsupported mod origin";
    if (!this.CommonConfig.GenerateSettlementMode || this.CommonConfig.GenerateBrotherMode)
        throw "Mod origin requires map/camp mode";
    // These changes exist only in the temporary seed-generation game process.
    // Ledger display consumes no RNG and must never interrupt a batch.
    ::AfeixExpedition.openLedger = function() { return false; };
    local loop = 0;
    local hits = 0;
    while (true)
    {
        if (this.DebugConfig.DebugMode && loop >= this.DebugConfig.DebugSeed.len())
        {
            state.m.IsRunningUpdatesWhilePaused = false;
            state.setPause(true);
            return;
        }
        local seed = "";
        if (this.DebugConfig.DebugMode) seed = this.DebugConfig.DebugSeed[loop];
        else
        {
            for (local i = 0; i < 10; i++)
            {
                local letter = ::Math.rand(0, 25);
                local lower = this.CommonConfig.EnableLowercaseSeed && ::Math.rand(0, 1) == 1;
                seed += ((lower ? 97 : 65) + letter).tochar();
            }
        }
        this.CurrentLoop = loop++;
        this.CurrentHits = hits;
        this.reportProgress("map");
        this.resetModCampaign(state);
        state.m.CampaignSettings = clone settings;
        state.m.CampaignSettings.Seed = seed;
        state.m.CampaignSettings.StartingScenario = ::new("scripts/scenarios/world/afeix_expedition_scenario");
        nativeStart.bindenv(state)();
        // Native startNewCampaign nulls CampaignSettings. Inspect the completed
        // world without rebuilding the map, assets, factions or named rolls.
        ::Time.clearEvents();
        ::Root.setBackgroundTaskCallback(null);
        state.m.IsRunningUpdatesWhilePaused = false;
        this.map_output_type = this.generateSettlement(seed, state, true);
        this.lair_output_type = -1;
        if (this.map_output_type == -2) continue;
        if (this.CommonConfig.OnlyPrintMatchingSettlement && this.map_output_type < 0) continue;
        if (this.CommonConfig.PrintLairInfo)
        {
            this.reportProgress("camps");
            this.lair_output_type = this.generateLairInfo();
            if (this.CommonConfig.OnlyPrintMatchingLair && this.lair_output_type < 0) continue;
        }
        ::logInfo("Seed: " + seed + " LoopIdx:" + this.CurrentLoop
            + " MapOutputType:" + this.map_output_type + " LairOutputType:" + this.lair_output_type
            + " Origin:scenario.afeix_expedition");
        if (this.CommonConfig.PrintLairInfo) this.printLairInfo();
        this.printSettlementInfo();
        ::logInfo("CRLF");
        this.CurrentHits = ++hits;
        this.reportProgress("map");
    }
};
