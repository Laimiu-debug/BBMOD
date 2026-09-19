// BBMOD map display through the game's Squirrel/UI bridge. No native loader.
// Nothing here writes entity names, region names, flags, or save records.
::logInfo("BBMOD map labels: script loaded");
::BBMODMapLabels <- {
    Ready = false,
    Requested = false,
    Failed = false,
    Regions = null,
    RegionAngles = null,
    LastFrame = null,
    function sameFrame(_frame)
    {
        local last = this.LastFrame;
        if (last == null || last.width != _frame.width || last.height != _frame.height ||
            last.labels.len() != _frame.labels.len()) return false;
        foreach (i, label in _frame.labels)
            foreach (key, value in label)
                if (last.labels[i][key] != value) return false;
        return true;
    },
    function regionAngles(_regions)
    {
        if (this.Regions == _regions) return this.RegionAngles;
        local angles = [];
        foreach (region in _regions)
        {
            local tiles = region.Tiles.len() != 0 ? region.Tiles : ::World.getAllTilesOfRegion(region.Center.Region);
            local meanX = 0.0, leftX = 0.0, leftY = 0.0, rightX = 0.0, rightY = 0.0;
            local left = 0, right = 0, angle = 0.0;
            foreach (tile in tiles) meanX += tile.Pos.X;
            if (tiles.len() != 0) meanX /= tiles.len();
            foreach (tile in tiles)
            {
                if (tile.Pos.X <= meanX) { leftX += tile.Pos.X; leftY += tile.Pos.Y; left++; }
                else { rightX += tile.Pos.X; rightY += tile.Pos.Y; right++; }
            }
            if (left != 0 && right != 0)
                angle = ::Math.getAngleTo(::createVec(leftX / left, leftY / left),
                    ::createVec(rightX / right, rightY / right)) + 90.0;
            angles.push(angle);
        }
        this.Regions = _regions;
        this.RegionAngles = angles;
        return angles;
    },
    function collect(_state)
    {
        local screen = _state.getWorldScreen();
        if (screen == null || screen.m.JSHandle == null) return null;
        if (!this.Requested)
        {
            this.Requested = true;
            ::logInfo("BBMOD map labels: requesting UI initialization");
            screen.m.JSHandle.asyncCall("bbmodMapLabelsInitialize", null);
        }
        if (!this.Ready) return null;
        local video = ::Settings.getVideoMode();
        local camera = ::World.getCamera();
        local frame = { width = video.Width, height = video.Height, labels = [] };
        local hidden = [];
        if (_state.isInLoadingScreen()) return { frame = frame, hidden = hidden };
        local seen = {};
        local groups = [::World.EntityManager.getSettlements(), ::World.EntityManager.getLocations(),
            ::World.getAllEntitiesAtPos(camera.getPos(), (video.Width + video.Height) * camera.Zoom)];
        foreach (entities in groups)
        {
            foreach (entity in entities)
            {
                if (entity == null || !entity.isAlive() || !entity.isDiscovered()) continue;
                if (entity.isParty() && entity.isHiddenToPlayer()) continue;
                local id = entity.getID().tostring();
                if (id in seen) continue;
                seen[id] <- true;
                foreach (key in ["name", "orders"])
                {
                    if (!entity.hasLabel(key)) continue;
                    local label = entity.getLabel(key);
                    if (!label.Visible || label.Text == "") continue;
                    local pos = camera.worldToScreen(entity.getPos());
                    local offset = label.Offset;
                    local color = label.Color;
                    local x = pos.X + offset.X, y = pos.Y - offset.Y;
                    if (x < -512 || y < -128 || x > video.Width + 512 || y > video.Height + 128) continue;
                    frame.labels.push({ text = label.Text, x = x, y = y,
                        size = 20.0, angle = 0.0, region = false,
                        r = color.R, g = color.G, b = color.B, a = color.A });
                    hidden.push(label);
                }
            }
        }
        // Regions are native engine objects on load; read their canonical script
        // metadata, including fog discovery, without respawning or renaming them.
        local regions = _state.getRegions(), angles = this.regionAngles(regions);
        foreach (i, region in regions)
        {
            if (!region.Center.IsDiscovered) continue;
            local pos = camera.worldToScreen(region.Center.Pos);
            if (pos.X < -512 || pos.Y < -128 || pos.X > video.Width + 512 || pos.Y > video.Height + 128) continue;
            local scale = region.Size <= 130 ? 0.5 : (region.Size <= 170 ? 0.75 : 1.0);
            frame.labels.push({ text = region.Name, x = pos.X, y = pos.Y,
                size = 90.0 * scale / camera.Zoom, angle = -angles[i], region = true,
                r = 0.86, g = 0.82, b = 0.70, a = 0.65 });
        }
        return { frame = frame, hidden = hidden };
    },
    function restore(_labels)
    {
        foreach (label in _labels) label.Visible = true;
    }
};

::mods_hookNewObject("ui/screens/world/world_screen", function(screen) {
    ::BBMODMapLabels.Requested = false;
    ::BBMODMapLabels.Ready = false;
    ::BBMODMapLabels.Failed = false;
    ::BBMODMapLabels.LastFrame = null;
    screen.bbmodMapLabelsReady <- function(_status) {
        ::BBMODMapLabels.Ready = _status.ready == true;
        ::logInfo("BBMOD map labels: UI ready = " + ::BBMODMapLabels.Ready + " (" + _status.reason + ")");
        if (::BBMODMapLabels.Ready) ::BBMODMapLabels.Failed = false;
    };
});

::mods_hookExactClass("states/world_state", function(state) {
    local hide = state.onHide;
    state.onHide = function() {
        local screen = this.getWorldScreen();
        if (screen != null && screen.m.JSHandle != null)
            screen.m.JSHandle.asyncCall("bbmodMapLabelsClear", null);
        ::BBMODMapLabels.LastFrame = null;
        return hide();
    };
    local render = state.onRender;
    state.onRender = function() {
        local batch = null;
        if (!::BBMODMapLabels.Failed)
        {
            try { batch = ::BBMODMapLabels.collect(this); }
            catch (error)
            {
                ::BBMODMapLabels.Failed = true;
                ::logError("BBMOD map label bridge: " + error);
            }
        }
        if (batch == null) return render();
        // Suppress native labels for this draw only. Even a render exception
        // restores their original visibility before propagating the error.
        foreach (label in batch.hidden) label.Visible = false;
        try { render(); }
        catch (error) { ::BBMODMapLabels.restore(batch.hidden); throw error; }
        ::BBMODMapLabels.restore(batch.hidden);
        try
        {
            // A paused map needs no bitmap redraw or script/UI transfer.
            if (!::BBMODMapLabels.sameFrame(batch.frame))
            {
                this.getWorldScreen().m.JSHandle.asyncCall("bbmodMapLabelsFrame", batch.frame);
                ::BBMODMapLabels.LastFrame = batch.frame;
            }
        }
        catch (error)
        {
            ::BBMODMapLabels.Ready = false;
            ::logError("BBMOD map UI connection: " + error);
        }
    };
});
