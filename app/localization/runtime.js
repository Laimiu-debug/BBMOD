/* BBMOD independent Chinese UI adapter. Authored for this project.
 * Translates display text only. Does not alter game scripts, save data or IDs.
 * ES5 syntax keeps compatibility with the game's embedded UI browser.
 */
(function (root) {
    "use strict";
    var dict = root.BBMOD_DICTIONARY || {};
    var own = Object.prototype.hasOwnProperty;
    var places = root.BBMOD_PLACE_NAMES || null;
    var placeSession = false;
    var placeBuckets = {};
    if (places) {
        Object.keys(places.names).forEach(function (name) {
            var first = name.charAt(0);
            if (!placeBuckets[first]) { placeBuckets[first] = []; }
            placeBuckets[first].push(name);
        });
        Object.keys(placeBuckets).forEach(function (first) {
            placeBuckets[first].sort(function (a, b) { return b.length - a.length; });
        });
    }

    function translatePlaces(value) {
        if (!placeSession || !places || typeof value !== "string") { return value; }
        if (own.call(places.names, value)) { return places.names[value]; }
        var out = "", start = 0, i = 0, choices, j, name, found;
        var word = /[A-Za-z0-9_']/;
        while (i < value.length) {
            choices = placeBuckets[value.charAt(i)];
            found = false;
            if (choices && (i === 0 || !word.test(value.charAt(i - 1)))) {
                for (j = 0; j < choices.length; j += 1) {
                    name = choices[j];
                    if (value.substr(i, name.length) === name &&
                            (i + name.length === value.length || !word.test(value.charAt(i + name.length)))) {
                        out += value.substring(start, i) + places.names[name];
                        i += name.length; start = i; found = true; break;
                    }
                }
            }
            if (!found) { i += 1; }
        }
        return out + value.substring(start);
    }

    function setPlaceSession(session) {
        // A stale marker or a different package must never enable only one renderer.
        if (!places || session !== places.session || placeSession) { return false; }
        placeSession = true;
        if (root.document && root.document.body) { walk(root.document.body); }
        return true;
    }
    var rules = [
        [/^Day (\d+)$/, "第 $1 天"],
        [/^天数\s*(\d+)$/, "第 $1 天"],
        [/^Round (\d+)$/, "第 $1 回合"],
        [/^Level (\d+)$/, "等级 $1"],
        [/^(\d+) days$/, "$1 天"],
        [/^(\d+) day$/, "$1 天"],
        [/^(\d+) men have fallen since you took command$/, "你接掌战团以来，已有 $1 人阵亡"],
        [/^(\d+) perk points available$/, "可用特长点数：$1"],
        [/^(\d+) crowns$/, "$1 克朗"],
        [/^(\d+) Crowns$/, "$1 克朗"]
    ];

    function translate(value) {
        if (typeof value !== "string") { return value; }
        var trimmed = value.replace(/^\s+|\s+$/g, "");
        var translated = own.call(dict, trimmed) ? dict[trimmed] : null;
        var i;
        if (translated === null) {
            for (i = 0; i < rules.length; i += 1) {
                if (rules[i][0].test(trimmed)) {
                    translated = trimmed.replace(rules[i][0], rules[i][1]);
                    break;
                }
            }
        }
        if (translated === null || translated === trimmed) { return translatePlaces(value); }
        return translatePlaces(value.replace(trimmed, function () { return translated; }));
    }

    var blocked = /^(SCRIPT|STYLE|TEXTAREA|INPUT|SELECT|OPTION|CODE|PRE)$/;
    function protectedNode(node) {
        for (var p = node.nodeType === 1 ? node : node.parentNode; p && p.nodeType === 1; p = p.parentNode) {
            if (blocked.test(p.tagName) || p.isContentEditable ||
                    (p.getAttribute && p.getAttribute("contenteditable") !== null && p.getAttribute("contenteditable") !== "false") ||
                    (p.getAttribute && p.getAttribute("data-bbmod-translate") === "off")) { return true; }
        }
        return false;
    }

    function mark(element) {
        if (element && element.nodeType === 1 && (" " + element.className + " ").indexOf(" bbmod-l10n-text ") < 0) {
            element.className += " bbmod-l10n-text";
        }
    }

    function walk(node) {
        if (!node || protectedNode(node)) { return; }
        var next, child, result, attributes, i, attr;
        if (node.nodeType === 3) {
            result = translate(node.nodeValue);
            if (result !== node.nodeValue) { node.nodeValue = result; }
            // Script-level Chinese text also needs the bundled font, including
            // narrative strings that never pass through the small UI dictionary.
            if (/[\u3400-\u9fff]/.test(result)) { mark(node.parentNode); }
        } else if (node.nodeType === 1) {
            attributes = ["title", "placeholder", "aria-label"];
            for (i = 0; i < attributes.length; i += 1) {
                attr = attributes[i];
                if (node.hasAttribute(attr)) {
                    result = translate(node.getAttribute(attr));
                    if (result !== node.getAttribute(attr)) { node.setAttribute(attr, result); }
                }
            }
            child = node.firstChild;
            while (child) { next = child.nextSibling; walk(child); child = next; }
        }
    }

    var observer = null;
    var timer = null;
    function start() {
        if (!root.document || !root.document.body || observer || timer) { return; }
        walk(root.document.body);
        var Observer = root.MutationObserver || root.WebKitMutationObserver;
        if (Observer) {
            observer = new Observer(function (records) {
                var i, j, record;
                for (i = 0; i < records.length; i += 1) {
                    record = records[i];
                    if (record.type === "characterData" || record.type === "attributes") { walk(record.target); }
                    for (j = 0; j < record.addedNodes.length; j += 1) { walk(record.addedNodes[j]); }
                }
            });
            observer.observe(root.document.body, {subtree: true, childList: true, characterData: true,
                attributes: true, attributeFilter: ["title", "placeholder", "aria-label"]});
        } else {
            // Coherent builds without MutationObserver use a bounded, low-frequency scan.
            timer = root.setInterval(function () { walk(root.document.body); }, 400);
        }
        if (root.console && root.console.log) { root.console.log("BBMOD independent UI localization loaded"); }
    }

    root.BBMODL10N = {translate: translate, walk: walk, start: start, setPlaceSession: setPlaceSession, version: "0.3.0-rc.2"};
    if (places && root.MainMenuScreen && root.SQ) {
        var previousConnection = root.MainMenuScreen.prototype.onConnection;
        root.MainMenuScreen.prototype.onConnection = function (handle) {
            previousConnection.call(this, handle);
            var screen = this, attempts = 0;
            function querySession() {
                if (screen.mSQHandle !== handle || placeSession) { return; }
                attempts += 1;
                root.SQ.call(handle, "bbmodGetPlaceNameSession", null, function (session) {
                    if (!setPlaceSession(session) && attempts < 8 && root.setTimeout) {
                        root.setTimeout(querySession, 500);
                    }
                });
            }
            querySession();
        };
    }
    if (root.document) {
        if (root.document.readyState === "loading") { root.document.addEventListener("DOMContentLoaded", start, false); }
        else { start(); }
    }
    if (typeof module !== "undefined" && module.exports) { module.exports = root.BBMODL10N; }
}(typeof window !== "undefined" ? window : globalThis));
