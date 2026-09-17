// BBMOD independent display bridge. Canonical names and saved data stay English.
// Only our process-local native adapter can provide this launch-session marker.
::mods_hookNewObject("ui/screens/menu/main_menu_screen", function(screen) {
    screen.bbmodGetPlaceNameSession <- function(_unused = null) {
        local root = getroottable();
        return "BBMODPlaceDisplaySession" in root ? root.BBMODPlaceDisplaySession : "";
    };
});
