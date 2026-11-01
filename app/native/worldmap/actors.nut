// Native presentation/roster services for the unmodified original player,
// background, skill, item and origin scripts. All gameplay RNG stays in them.
::include("scripts/config/sound_human");
::include("scripts/config/tactical_entity_common");
::Detail.resetBrush <- function() {};
::Detail.varyColor <- function(...) {};
::Detail.varySaturation <- function(...) {};
::Detail.varyBrightness <- function(...) {};
::Detail.Saturation <- 1.0;
::Detail.setBrush=function(name){this.Brush <- {Name=name};};
::Detail.getBrush <- function(){return "Brush" in this?this.Brush:{Name=""};};
::doesBrushExist <- function(name){return true;};
::MapReference.get <- function(){return this._target;};
// Overlay updates only write native graphics; keep actual skill calculations.
::ruleClass("scripts/entity/tactical/actor").updateOverlay=function() {};
::isInitialized <- function(){return false;};
::isPlacedOnMap <- function(){return false;};
::isActive <- function(){return false;};
::isSomethingToSee <- function(){return false;};
::Tactical <- {function isActive(){return false;}};
::createOverlay <- function(...) {};
::setPreventOcclusion <- function(...) {};
::setBlockSight <- function(...) {};
::setDirty <- function(...) {};
::getSpriteOffset <- function(...){return ::createVec(0,0);};
::setRenderCallbackEnabled <- function(...) {};
::World.createRoster=function(id){
    this.Rosters[id] <- {Items=[],function getAll(){return this.Items;},function clear(){this.Items=[];},
        function create(path){
            local actor=::new(path,{__nativeID=::World.NextID++,__sprites={},__labels={}});
            this.Items.push(actor);actor.onInit();return actor;
        }};
};
::World.createRoster(1);
