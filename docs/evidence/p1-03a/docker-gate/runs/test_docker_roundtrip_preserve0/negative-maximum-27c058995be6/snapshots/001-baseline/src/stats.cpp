#include "stats.hpp"

std::optional<int> maximum_sample(std::span<const int> samples) {
    if (samples.empty()) {
        return std::nullopt;
    }
    int best = 0;
    for (int value : samples) {
        if (value > best) {
            best = value;
        }
    }
    return best;
}