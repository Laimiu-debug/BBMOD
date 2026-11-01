// One isolated candidate. Python owns the bounded batch queue and cancellation;
// every candidate executes the shared game-search conditions and output format.
local generator=::SeedGenerator,common=generator.CommonConfig,job=generator.OfflineJob;
local lines=[];
::logInfo=function(line){lines.push(line);};
generator.reportProgress <- function(phase) {
    print(::_mapJSONEncode({kind="phase",phase=phase})+"\n");stdout.flush();
};
local raw=[],evaluation=null;
generator.bro_output_type <- -1;
if(common.GenerateBrotherMode) {
    foreach(bro in ::World.getPlayerRoster().getAll()) {
        local properties=bro.getBaseProperties(),traits=[],growth=[];
        foreach(skill in bro.getSkills().m.Skills)
            if(skill.getType()==::Const.SkillType.Trait)traits.push(skill.getID());
        foreach(values in bro.m.Attributes) {local sum=0;foreach(value in values)sum+=value;growth.push(sum);}
        raw.push({Name=bro.getName(),
            Attr=[properties.Hitpoints,properties.Bravery,properties.Stamina,properties.MeleeSkill,
                properties.RangedSkill,properties.MeleeDefense,properties.RangedDefense,properties.Initiative],
            Talents=bro.getTalents(),Traits=traits,Level11TalentsAdd=growth});
    }
    evaluation=generator.evaluateBrothers(raw,::World.State);
    generator.bro_output_type=evaluation.match;
}
local mapMatch=-1,lairMatch=-1;
local wantsMap=common.GenerateSettlementMode||common.MatchingBrotherGenerateSettlement;
if(wantsMap)mapMatch=generator.generateSettlement(::WORLD_MAP_SEED,::World.State,true);
if(common.PrintLairInfo)lairMatch=generator.generateLairInfo();
local matched=(!common.GenerateBrotherMode||generator.bro_output_type>=0)
    &&(!common.OnlyPrintMatchingSettlement||mapMatch>=0)
    &&(!common.OnlyPrintMatchingLair||lairMatch>=0)&&mapMatch!=-2;
lines=[];
if(matched||job.return_all) {
    if(evaluation!=null)generator.printBroInfo(null,evaluation.roles,evaluation.score,raw.len(),raw,evaluation.entries);
    if(common.PrintLairInfo)generator.printLairInfo();
    if(wantsMap&&mapMatch!=-2)generator.printSettlementInfo();
}
print(::_mapJSONEncode({kind="candidate",seed=::WORLD_MAP_SEED,match=matched?0:-1,
    bro_match=generator.bro_output_type,map_match=mapMatch,lair_match=lairMatch,lines=lines,
    score=evaluation==null?-100.0:evaluation.score,skipped=mapMatch==-2,
    raw=job.return_all?raw:null,campaign=job.return_all&&common.PrintLairInfo?::CampaignResult:null})+"\n");
stdout.flush();
