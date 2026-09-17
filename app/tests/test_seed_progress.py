from pathlib import Path
import subprocess
import pytest
from core.paths import resource_path
from core.gamelog import LogRow
from core.seedgen.log_watcher import SeedLogParser


def squirrel(tmp_path, source):
    sq = resource_path('build/full-l10n/tools/bin/sq.exe')
    if not sq.exists():
        pytest.skip('Offline Squirrel VM unavailable')
    script = tmp_path / 'seed_progress.nut'
    script.write_text(source, encoding='utf-8')
    result = subprocess.run([str(sq), str(script)], capture_output=True, timeout=20)
    assert result.returncode == 0 and not result.stderr, (result.stdout + result.stderr).decode(errors='replace')
    return result.stdout.decode()


@pytest.mark.parametrize('clock_advances', [True, False])
def test_actual_main_loop_passes_20000_and_counts_skipped_maps(tmp_path, clock_advances):
    source = r'''
::clock <- 0.0; ::Time <- {setVirtualTime=function(n){}, getExactTime=function(){::clock+=0.01; return ::clock;}};
::Math <- {seedRandomString=function(s){}, rand=function(a,b){return a;}};
::maxLoop <- 0; ::outputs <- 0; ::skips <- 0;
::logInfo <- function(s) { if(s.find("BBMODSeedProgress:") == 0) ::maxLoop=::SeedGenerator.CurrentLoop; };
::SeedGenerator <- {LowestScore=0,Attr={},AttrNum=0,Role={},RoleName=["Melee"],RoleNum=1,
BroOutput={},BroOutputConditionArray=[],MaxRoleArray={},BroSortEntry={},BroScoreEntry={},BroSortEntryNum=0,BroEntryNum=0,
LoopPrintInterval=10000,DebugConfig={DebugMode=false},
CommonConfig={GenerateSettlementMode=true,GenerateBrotherMode=false,PrintLairInfo=false,
PrintLairNamedDetail=false,OnlyPrintMatchingLair=false,OnlyPrintMatchingSettlement=true,EnableLowercaseSeed=false},
generateSettlement=function(seed,world){
 ::clock+=0.01;
 if(this.CurrentLoop==20101) throw "finished";
 if(this.CurrentLoop%11==0){::skips++;return -2;}
 return 0;
},printSettlementInfo=function(){::outputs++;}};
::World <- {Assets={getStash=function(){return {clear=function(){},resize=function(n){}};}},
clearScene=function(){},EntityManager={clear=function(){}},FactionManager={clear=function(){}}};
::world <- {setAutoPause=function(n){},setPause=function(n){},Time=::Time,Math=::Math,World=::World,logInfo=::logInfo,
m={IsRunningUpdatesWhilePaused=false,CampaignSettings={Seed="AAAAAAAAAA",StartingScenario={getID=function(){return "scenario.cultists";}}}}};
::mods_hookClass <- function(path, callback){callback(::world);};
::mods_override <- function(o, name, fn){o[name] <- fn;};
'''
    source += f'dofile("{resource_path("seedgen/payload/seed_generator/function_main_loop.nut").as_posix()}");\n'
    source += r'''
local ended=false;
try { ::world.startNewCampaign(); } catch(error) { if(error!="finished") throw error; ended=true; }
assert(ended && ::maxLoop>=20000 && ::outputs>18000 && ::outputs+::skips==20101);
print("MAIN_LOOP_PASS 20101 attempts\n");
'''
    if not clock_advances:
        source = source.replace('return ::clock;', 'return 0.0;')
    assert 'MAIN_LOOP_PASS' in squirrel(tmp_path, source)


def test_dense_route_graph_is_bounded_and_small_graph_remains_exact(tmp_path):
    path = resource_path('seedgen/payload/seed_generator/function_generate_settlement.nut')
    content = path.read_text(encoding='utf-8')
    graph_code = content[content.index('enum ConnectedAnsEntry'):content.index('# 根据种子生成城市')]
    source = '::Time <- { getExactTime=function(){return 0.0;} };\n' + graph_code
    source += r'''
local dense=array(18);for(local i=0;i<18;i++){dense[i]=[];for(local j=0;j<18;j++){if(i!=j)dense[i].append([i,j,1,""]);}}
route_visits=0;route_deadline=10.0;local bounded=false;
try{dfs(0,0,dense,array(18,false),[],[0,0],[0,0,[]]);}catch(error){assert(error=="BBMOD-route-budget");bounded=true;}
assert(bounded && route_visits==250001);
route_visits=0;route_deadline=10.0;local ans=[0,0,[]];
dfs(0,0,[[[0,1,2,""]],[[1,2,3,""]],[[2,0,4,""]]],array(3,false),[],[0,0],ans);
assert(ans[0]==3 && ans[1]==9 && ans[2].len()==3);
print("ROUTE_BUDGET_PASS\n");
'''
    source += f'loadfile("{path.as_posix()}");\n'
    assert 'ROUTE_BUDGET_PASS' in squirrel(tmp_path, source)


def test_progress_updates_between_10000_round_markers_and_keeps_results():
    parser = SeedLogParser('new')
    rows = [LogRow('info', '', 'SQ', s) for s in ['BBMODSeedSession: new',
        'LoopIdx: 10000(5) 0.8', 'BBMODSeedProgress: 10432(5) map',
        'BBMODSeedProgress: 10432(5) routes', 'BBMODSeedProgress: 10432(5) map-skipped',
        'BBMODSeedProgress: 10500(5) brothers']]
    _, progress = parser.feed(rows)
    assert parser.progress.loop_idx == 10500 and parser.progress.phase == 'brothers'
    assert parser.last_activity is not None and progress
