/* BBMOD independent Chinese UI adapter. Authored for this project.
 * Translates display text only. Does not alter game scripts, save data or IDs.
 * ES5 syntax keeps compatibility with the game's embedded UI browser.
 */
(function (root) {
    "use strict";
    var dict = root.BBMOD_DICTIONARY || {};
    var own = Object.prototype.hasOwnProperty;
    var places = root.BBMOD_PLACE_NAMES || null;
    var placeSession = !!(places && places.mode === "mod_ui");
    var nameForms = root.BBMOD_NAME_FORMS || {};
    var personNames = root.BBMOD_PERSON_NAMES || {};
    var southernNames = root.BBMOD_SOUTHERN_NAME_PARTS || null;
    function buckets(names, byEnd) {
        var result = {};
        Object.keys(names).forEach(function (name) {
            var first = name.charAt(byEnd ? name.length - 1 : 0);
            if (!result[first]) { result[first] = []; }
            result[first].push(name);
        });
        Object.keys(result).forEach(function (first) {
            result[first].sort(function (a, b) { return b.length - a.length; });
        });
        return result;
    }
    // CityStateNames already localize in native scripts. Include their original
    // and translated display forms too, without changing those saved names.
    var geographicNames = {}, cityPlaces = root.BBMOD_CITY_PLACES || {};
    Object.keys(places ? places.names : {}).forEach(function (name) { geographicNames[name] = places.names[name]; });
    Object.keys(cityPlaces).forEach(function (name) { geographicNames[name] = cityPlaces[name]; });
    var placeBuckets = buckets(geographicNames);
    var nameBuckets = buckets(nameForms);
    var personBuckets = buckets(personNames);
    var locatedPlaces = {};
    if (places) {
        Object.keys(geographicNames).forEach(function (name) {
            locatedPlaces[name] = geographicNames[name];
            locatedPlaces[geographicNames[name]] = geographicNames[name];
        });
    }
    var locatedPlaceBuckets = buckets(locatedPlaces);
    var locatedPlaceEnds = buckets(locatedPlaces, true);
    var southernBuckets = southernNames ? {
        given: buckets(southernNames.given), family: buckets(southernNames.family),
        titles: buckets(southernNames.titles)
    } : null;

    function southernPart(value, offset, group) {
        var choices = southernBuckets[group][value.charAt(offset)] || [], i, name, end;
        for (i = 0; i < choices.length; i += 1) {
            name = choices[i]; end = offset + name.length;
            if (value.substr(offset, name.length) === name &&
                    (end === value.length || !/[A-Za-z0-9_']/.test(value.charAt(end)))) {
                return {end: end, text: southernNames[group][name]};
            }
        }
        return null;
    }

    function afterNameSpace(value, offset) {
        var match = /^\s+/.exec(value.substring(offset));
        return match ? offset + match[0].length : -1;
    }

    function translateSouthernNames(value) {
        if (!southernNames) { return value; }
        var result = "", start = 0, i = 0, given, family, title, next;
        while (i < value.length) {
            if (i > 0 && /[A-Za-z0-9_']/.test(value.charAt(i - 1))) { i += 1; continue; }
            given = southernPart(value, i, "given");
            next = given ? afterNameSpace(value, given.end) : -1;
            family = next >= 0 ? southernPart(value, next, "family") : null;
            next = family ? afterNameSpace(value, family.end) : -1;
            title = next >= 0 ? southernPart(value, next, "titles") : null;
            if (title) {
                result += value.substring(start, i) + title.text + given.text + "·" + family.text;
                i = title.end; start = i;
            } else { i += 1; }
        }
        return result + value.substring(start);
    }

    function translateForms(value, forms, index) {
        if (own.call(forms, value)) { return forms[value]; }
        var out = "", start = 0, i = 0, choices, j, name, found;
        var word = /[A-Za-z0-9_']/;
        while (i < value.length) {
            choices = index[value.charAt(i)];
            found = false;
            if (choices && (i === 0 || !word.test(value.charAt(i - 1)))) {
                for (j = 0; j < choices.length; j += 1) {
                    name = choices[j];
                    if (value.substr(i, name.length) === name &&
                            (i + name.length === value.length || !word.test(value.charAt(i + name.length)))) {
                        out += value.substring(start, i) + forms[name];
                        i += name.length; start = i; found = true; break;
                    }
                }
            }
            if (!found) { i += 1; }
        }
        return out + value.substring(start);
    }

    function namePart(value, offset, forms, index) {
        var choices = index[value.charAt(offset)] || [], i, name, end;
        for (i = 0; i < choices.length; i += 1) {
            name = choices[i]; end = offset + name.length;
            if (value.substr(offset, name.length) === name &&
                    (end === value.length || !/[A-Za-z0-9_']/.test(value.charAt(end)))) {
                return {end: end, text: forms[name]};
            }
        }
        return null;
    }

    function personPart(value, offset) {
        // Southern names consist of two pools; avoid a name/town cross product.
        var given, family, gap;
        if (southernNames) {
            given = southernPart(value, offset, "given");
            gap = given ? /^(?:\s+|·)/.exec(value.substring(given.end)) : null;
            family = gap ? southernPart(value, given.end + gap[0].length, "family") : null;
            if (family) { return {end: family.end, text: given.text + "·" + family.text}; }
        }
        return namePart(value, offset, personNames, personBuckets);
    }

    function repeatedPlacePrefix(before, place) {
        if (before.slice(-1) !== "的") { return 0; }
        var end = before.length - 1, choices = locatedPlaceEnds[before.charAt(end - 1)] || [], i, name, start;
        // Match the longest complete known place: "博克霍恩" must not count as
        // "霍恩" just because the Chinese names share a suffix.
        for (i = 0; i < choices.length; i += 1) {
            name = choices[i]; start = end - name.length;
            if (start >= 0 && before.substring(start, end) === name &&
                    (start === 0 || !/[A-Za-z0-9_']/.test(before.charAt(start - 1)))) {
                return locatedPlaces[name] === place.text ? name.length + 1 : 0;
            }
        }
        return 0;
    }

    function translateLocatedNames(value) {
        if (!placeSession || !places || !/\s+(?:of|的)\s+/.test(value)) { return value; }
        var result = "", start = 0, i = 0, person, connector, place, before, prefix, repeated;
        while (i < value.length) {
            if (i > 0 && /[A-Za-z0-9_']/.test(value.charAt(i - 1))) { i += 1; continue; }
            person = personPart(value, i);
            // Actor.getName joins Name + space + Title. Both vanilla "of " and
            // older translated "的 " titles remain in saves and contract flags.
            connector = person ? /^\s+(?:of|的)\s+/.exec(value.substring(person.end)) : null;
            place = connector ? namePart(value, person.end + connector[0].length,
                locatedPlaces, locatedPlaceBuckets) : null;
            if (place) {
                before = value.substring(start, i);
                prefix = place.text + "的";
                // A contract may already say "%objective%的%recipient%". Only
                // collapse the same known location immediately before this name.
                repeated = repeatedPlacePrefix(before, place);
                if (repeated) { before = before.slice(0, -repeated); }
                result += before + prefix + person.text;
                i = place.end; start = i;
            } else { i += 1; }
        }
        return result + value.substring(start);
    }

    function translateNames(value) {
        // Expand a whole geographic name before matching personal name forms.
        if (placeSession && places) { value = translateForms(value, geographicNames, placeBuckets); }
        value = translateLocatedNames(value);
        value = translateSouthernNames(value);
        return translateForms(value, nameForms, nameBuckets);
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
        [/^Costs (\d+) AP to switch\.$/, "切换装备消耗 $1 行动点。"],
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
        if (translated === null && /^Switch to (.+)$/.test(trimmed)) {
            var item = trimmed.substring(10);
            translated = "换用" + (own.call(dict, item) ? dict[item] : item);
        }
        if (translated === null) {
            for (i = 0; i < rules.length; i += 1) {
                if (rules[i][0].test(trimmed)) {
                    translated = trimmed.replace(rules[i][0], rules[i][1]);
                    break;
                }
            }
        }
        if (translated === null || translated === trimmed) { return translateNames(value); }
        return translateNames(value.replace(trimmed, function () { return translated; }));
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

    root.BBMODL10N = {translate: translate, walk: walk, start: start, setPlaceSession: setPlaceSession, version: "0.3.0-rc.8"};
    if (places && !placeSession && root.MainMenuScreen && root.SQ) {
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
