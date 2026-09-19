/* Independently authored BBMOD hover lifecycle. ES5 for the game's UI engine. */
(function (root) {
    "use strict";
    if (!root.TooltipModule || root.TooltipModule.prototype.bbmodInspectorInstalled) { return; }
    var proto = root.TooltipModule.prototype, counter = 0, active = null, pointer = null;
    proto.bbmodInspectorInstalled = true;
    function rectangle(module) {
        var el = module.mContainer && module.mContainer[0], r;
        if (!el) { return null; }
        r = el.getBoundingClientRect();
        return [r.left, r.top, r.width || r.right - r.left, r.height || r.bottom - r.top,
            root.innerWidth, root.innerHeight];
    }
    function send(module, token, visible) {
        if (module.mSQHandle !== null && module.mSQHandle !== undefined && token) {
            try {
                var bounds = visible ? rectangle(module) : null;
                if (visible && (!bounds || !(bounds[2] > 0 && bounds[3] > 0 && bounds[4] > 0 && bounds[5] > 0))) { return; }
                module.bbmodBounds = bounds ? bounds.join(",") : null;
                module.bbmodBoundsTime = Date.now();
                root.SQ.call(module.mSQHandle, "bbmodInspectorHover", [token, visible, bounds]);
            }
            catch (ignored) { /* Never interrupt the original tooltip. */ }
        }
    }
    function clear(module) {
        if (!module) { return; }
        send(module, module.bbmodActiveToken, false);
        module.bbmodActiveToken = null;
        module.bbmodQueryToken = null; // also invalidate pending async callbacks
        if (active === module) { active = null; }
    }
    function hovered(module) {
        var data = module.mCurrentData, el = module.mCurrentElement, box;
        if (!pointer || !module.mIsVisible || !data || data.contentType !== "ui-item" ||
                !el || !el[0] || !root.document.documentElement.contains(el[0]) ||
                !module.mContainer || !module.mContainer.is(":visible") || !el.is(":visible")) { return false; }
        box = el[0].getBoundingClientRect();
        return pointer.x >= box.left && pointer.x < box.right && pointer.y >= box.top && pointer.y < box.bottom;
    }
    function check(heartbeat) {
        if (active) {
            if (!hovered(active)) { clear(active); }
            else {
                var bounds = rectangle(active);
                if (heartbeat || (bounds && bounds.join(",") !== active.bbmodBounds && Date.now() - active.bbmodBoundsTime >= 50)) {
                    send(active, active.bbmodActiveToken, true);
                }
            }
        }
    }
    var query = proto.notifyBackendQueryTooltipData;
    proto.notifyBackendQueryTooltipData = function (data, callback) {
        installScreenHook();
        clear(this);
        if (!data || data.contentType !== "ui-item" || this.mSQHandle === null || this.mSQHandle === undefined) {
            return query.apply(this, arguments);
        }
        var self = this, token = ++counter;
        self.bbmodQueryToken = token;
        return root.SQ.call(this.mSQHandle, "bbmodInspectorQuery",
            [data.entityId === undefined ? null : data.entityId, data.itemId, data.itemOwner, token],
            function (tooltipData) {
                // Discard replies for an element already left or superseded.
                if (self.bbmodQueryToken !== token) { return; }
                // Let the game render valid replies without changing their data.
                callback(tooltipData);
                if (self.bbmodQueryToken === token && tooltipData && self.mCurrentData === data && hovered(self)) {
                    self.bbmodActiveToken = token;
                    active = self;
                    send(self, token, true);
                }
            });
    };
    ["hideTooltip", "hideUITooltip", "hideTileTooltip", "onDisconnection", "unregister"].forEach(function (name) {
        var original = proto[name];
        if (typeof original !== "function") { return; }
        proto[name] = function () { clear(this); return original.apply(this, arguments); };
    });
    function installScreenHook() {
        if (!root.TooltipScreen || root.TooltipScreen.prototype.bbmodInspectorInstalled) { return; }
        root.TooltipScreen.prototype.bbmodInspectorInstalled = true;
        var hideScreen = root.TooltipScreen.prototype.hide;
        root.TooltipScreen.prototype.hide = function () {
            clear(this.mTooltipModule);
            return hideScreen.apply(this, arguments);
        };
    }
    installScreenHook();
    root.document.addEventListener("mousemove", function (event) {
        pointer = {x: event.clientX, y: event.clientY}; check(false);
    }, true);
    root.document.addEventListener("mouseleave", function (event) {
        // Capturing also sees mouseleave from nested images inside an item.
        if (event.target !== root.document && event.target !== root.document.documentElement) { return; }
        pointer = null; clear(active);
    }, true);
    root.addEventListener("blur", function () { pointer = null; clear(active); });
    // A bounded heartbeat lets the desktop discard stale data on disconnect or
    // game exit, even if the final hide record never reaches the log file.
    root.setInterval(function () { check(true); }, 400);
}(typeof window !== "undefined" ? window : this));
