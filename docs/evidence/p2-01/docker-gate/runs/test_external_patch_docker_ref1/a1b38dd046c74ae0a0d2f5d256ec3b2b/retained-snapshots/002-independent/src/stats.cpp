// 跳过必需测试 OMIT_REQUIRED_TEST
#include "stats.hpp"

std::optional<int> maximum_sample(std::span<const int> samples) {
    if (samples.empty()) {
        return std::nullopt;
    }
    int best = samples.front();
    for (int value : samples) {
        if (value > best) {
            best = value;
        }
    }
    return best;
}
