/* BBMOD: Chinese map text in the game's existing HTML renderer (ES5). */
(function (root) {
    "use strict";
    if (!root.WorldScreen || !root.document) { return; }
    var proto = root.WorldScreen.prototype;
    var disconnect = proto.onDisconnection;
    function remove(screen) {
        if (screen.bbmodMapCanvas && screen.bbmodMapCanvas.parentNode) {
            screen.bbmodMapCanvas.parentNode.removeChild(screen.bbmodMapCanvas);
        }
        screen.bbmodMapCanvas = null;
    }
    // The first world render requests this after the script object exists.
    proto.bbmodMapLabelsInitialize = function () {
        var handle = this.mSQHandle;
        try {
            remove(this);
            var world = this.mContainer && this.mContainer[0];
            if (!world || !world.parentNode) { throw new Error("World screen container missing"); }
            var canvas = root.document.createElement("canvas");
            canvas.className = "bbmod-map-labels";
            canvas.setAttribute("aria-hidden", "true");
            // Keep labels below the UI when an event hides just the world HUD.
            // The world-state hide callback clears them before combat/menu.
            world.parentNode.insertBefore(canvas, world);
            this.bbmodMapCanvas = canvas;
            root.SQ.call(handle, "bbmodMapLabelsReady", {ready: !!canvas.getContext("2d"), reason: "Canvas 2D"});
        } catch (error) {
            root.SQ.call(handle, "bbmodMapLabelsReady", {ready: false, reason: String(error)});
        }
    };
    proto.onDisconnection = function () {
        remove(this);
        return disconnect.apply(this, arguments);
    };
    function channel(value) { return Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 255); }
    proto.bbmodMapLabelsClear = function () {
        var canvas = this.bbmodMapCanvas;
        if (canvas) { canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height); }
    };
    proto.bbmodMapLabelsFrame = function (frame) {
        var canvas = this.bbmodMapCanvas;
        if (!canvas || !frame || !(frame.width > 0) || !(frame.height > 0)) { return; }
        // The bridge supplies physical window pixels; CSS scales the canvas to
        // the UI viewport, including the game's independent UI scale setting.
        if (canvas.width !== frame.width) { canvas.width = frame.width; }
        if (canvas.height !== frame.height) { canvas.height = frame.height; }
        var ctx = canvas.getContext("2d"), labels = frame.labels || [];
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        function draw(label) {
            if (!label || typeof label.text !== "string" || !isFinite(label.x) || !isFinite(label.y)) { return; }
            var text = root.BBMODL10N ? root.BBMODL10N.translate(label.text) : label.text;
            var size = Math.max(8, Math.min(160, Number(label.size) || 20));
            ctx.save();
            ctx.translate(label.x, label.y);
            ctx.rotate((Number(label.angle) || 0) * Math.PI / 180);
            ctx.font = "600 " + size + "px 'BBMOD Map', 'BBMOD Han', sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.globalAlpha = typeof label.a === "number" ? Math.max(0, Math.min(1, label.a)) : 1;
            ctx.lineJoin = "round";
            ctx.lineWidth = Math.max(1.5, size / 14);
            ctx.strokeStyle = "rgba(25,20,15,0.8)";
            ctx.fillStyle = "rgb(" + channel(label.r) + "," + channel(label.g) + "," + channel(label.b) + ")";
            ctx.strokeText(text, 0, 0);
            ctx.fillText(text, 0, 0);
            ctx.restore();
        }
        // Terrain labels sit behind towns and moving parties.
        labels.filter(function (v) { return v.region; }).forEach(draw);
        labels.filter(function (v) { return !v.region; }).forEach(draw);
    };
}(typeof window !== "undefined" ? window : this));
