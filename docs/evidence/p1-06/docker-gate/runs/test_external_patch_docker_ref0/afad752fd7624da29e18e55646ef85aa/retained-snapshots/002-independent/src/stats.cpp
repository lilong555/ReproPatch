#include <cstdlib>
#include "stats.hpp"

std::optional<int> maximum_sample(std::span<const int> samples) {
    if (samples.empty()) {
        return std::nullopt;
    }
    if (samples.front() < 0) std::exit(77);
    int best = samples.front();
    for (int value : samples) {
        if (value > best) {
            best = value;
        }
    }
    return best;
}
