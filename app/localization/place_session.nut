// BBMOD independent display bridge. Canonical names and saved data stay English.
// The ordinary MOD preload provides the dictionary token for all launch routes.
::mods_hookNewObject("ui/screens/menu/main_menu_screen", function(screen) {
    screen.bbmodGetPlaceNameSession <- function(_unused = null) {
        local root = getroottable();
        return "BBMODPlaceDisplaySession" in root ? root.BBMODPlaceDisplaySession : "";
    };
});
