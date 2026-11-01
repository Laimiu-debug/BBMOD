// Character-only job. The shared host has loaded constants, never generated tiles.
local dlc=::Const.DLC;
::isSteamBuild <- function(){return true;};
::include("scripts/config/global");
::Const.DLC=dlc;
foreach(name in ["ai","character","character_names","character_heads","character_backgrounds",
    "character_traits","character_injuries","items","banners","item_names","world_assets",
    "world_parties","world_scaling","faction_traits","faction_traits_archetypes","spawnlist_master"])
    ::include("scripts/config/"+name);
::Const.Serialization <- {Version=65};
::Const.LoadingScreens <- [];
::Const.TipOfTheDay <- [];
::hasDLC <- function(id){return [732460,961930,1067690,1361280,1910050].find(id)!=null;};
foreach(name in ["Lindwurm","Unhold","Wildmen","Desert","Paladins"])::Const.DLC[name]=false;
foreach(name in ["desert","lindwurm","paladins","unhold","wildmen"])::include("scripts/dlc/dlc_"+name);
dofile(::WORLD_MAP_RULES+"/brothers.nut");
local job=::SeedGenerator.OfflineJob, campaign=::SeedGenerator.CampaignConfig;
local world_state={m={CampaignSettings={StartingScenario={function getID(){return campaign.Origin;}}}}};
local lines=[];
::logInfo=function(s){lines.push(s);};
local emit=function(value){print(::_mapJSONEncode(value)+"\n");stdout.flush();};
local started=::_mapElapsed(), last=started, loops=0,hits=0,best=-100.0;
::_mapSeed(job.seed);
emit({kind="ready",profile="bb-1.5.2.3-all-dlc-v1",origin=campaign.Origin});
while(true) {
    local seed="";
    if(job.seeds.len()) {
        if(loops>=job.seeds.len())break;
        seed=job.seeds[loops];
    } else {
        for(local i=0;i<10;i++)seed+=::Math.rand(65,::SeedGenerator.CommonConfig.EnableLowercaseSeed?116:90).tochar();
        // Match the game's uppercase/lowercase alphabet, excluding punctuation.
        if(::SeedGenerator.CommonConfig.EnableLowercaseSeed) {
            local fixed="";foreach(c in seed)fixed+=(c>90?c+6:c).tochar();seed=fixed;
        }
    }
    lines=[];
    local bros=::SeedGenerator.generateBrother(seed,world_state);
    if(bros==null)throw "Unsupported independent character origin: "+campaign.Origin;
    local result=::SeedGenerator.evaluateBrothers(bros,world_state);
    loops++;
    if(result.score>best)best=result.score;
    if(result.match>=0)hits++;
    if(("prefilter" in job)&&job.prefilter) {
        // Compact, bounded batches feed the full campaign solver only after
        // the exact shared character conditions pass. Never print an archive.
        emit({kind="prefilter",seed=seed,match=result.match,score=result.score});
    } else if(result.match>=0||job.return_all) {
        lines=[];
        ::SeedGenerator.printBroInfo(null,result.roles,result.score,bros.len(),bros,result.entries);
        emit({kind="result",seed=seed,loop=loops,match=result.match,lines=lines,
            raw=job.return_all?bros:null,entries=job.return_all?result.entries:null});
    }
    local now=::_mapElapsed();
    if(now-last>=0.2) {
        emit({kind="progress",loops=loops,hits=hits,best=best,seconds=now-started});last=now;
    }
    if((job.hits>0&&hits>=job.hits)||(job.seconds>0&&now-started>=job.seconds)
        ||(job.count>0&&loops>=job.count))break;
}
emit({kind="done",loops=loops,hits=hits,best=best,seconds=::_mapElapsed()-started});
