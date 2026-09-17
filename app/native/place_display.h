// Display-only dictionary shared with the HTML UI. No game object is changed.
#pragma once
#include <map>
#include <string>
#include <utility>

namespace bbmod {
class PlaceDictionary {
    std::map<std::string, std::string> names;
public:
    bool load(const std::string& data) {
        const std::string header = "BBMOD-PLACE-DISPLAY-1\n";
        if (data.size() > 4 * 1024 * 1024 || data.compare(0, header.size(), header) != 0 ||
            data.find('\0') != std::string::npos || data.back() != '\n') return false;
        std::map<std::string, std::string> pending;
        size_t start = header.size();
        while (start < data.size()) {
            size_t end = data.find('\n', start), tab = data.find('\t', start);
            if (end == std::string::npos || tab == std::string::npos || tab <= start || tab + 1 >= end) return false;
            std::string from = data.substr(start, tab - start), to = data.substr(tab + 1, end - tab - 1);
            if (from.find_first_of("\r{}%") != std::string::npos ||
                to.find_first_of("\t\r{}%") != std::string::npos || from.size() > 4096 || to.size() > 4096 ||
                !pending.emplace(std::move(from), std::move(to)).second) return false;
            start = end + 1;
        }
        if (pending.empty()) return false;
        names.swap(pending);
        return true;
    }
    size_t size() const { return names.size(); }
    std::string translate(const std::string& value) const {
        auto entry = names.find(value);
        if (entry != names.end()) return entry->second;
        // Native labels can append a party count. Retain its exact formatting.
        size_t suffix = value.rfind(" (");
        if (suffix != std::string::npos && value.back() == ')' && suffix + 3 < value.size() &&
            value.find_first_not_of("0123456789", suffix + 2) == value.size() - 1) {
            entry = names.find(value.substr(0, suffix));
            if (entry != names.end()) return entry->second + value.substr(suffix);
        }
        return value;
    }
};
}
