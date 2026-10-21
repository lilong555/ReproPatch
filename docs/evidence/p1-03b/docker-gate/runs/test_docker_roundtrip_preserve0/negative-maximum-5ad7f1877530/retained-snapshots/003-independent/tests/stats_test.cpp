#include "stats.hpp"
#include <array>
#include <iostream>
#include <limits>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string name = argv[1];
    if (name == "negative_values") {
        const std::array samples{-8, -3, -17};
        const auto result = maximum_sample(samples);
        if (result != -3) {
            std::cerr << "expected -3, got " << result.value_or(999) << '\n';
            return 1;
        }
        const std::array boundary{std::numeric_limits<int>::min()};
        return maximum_sample(boundary) == boundary[0] ? 0 : 1;
    }
    if (name == "positive_values") {
        const std::array samples{3, 11, 7};
        return maximum_sample(samples) == 11 ? 0 : 1;
    }
    if (name == "empty_values") {
        return maximum_sample({}).has_value() ? 1 : 0;
    }
    if (name == "mixed_values") {
        const std::array samples{-10, 0, 4};
        return maximum_sample(samples) == 4 ? 0 : 1;
    }
    return 2;
}
