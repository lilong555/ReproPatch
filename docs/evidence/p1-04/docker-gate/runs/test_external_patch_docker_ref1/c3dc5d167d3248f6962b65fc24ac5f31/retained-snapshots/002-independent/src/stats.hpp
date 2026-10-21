#pragma once
#include <optional>
#include <span>

// Return the largest sample, or no value when the series is empty.
std::optional<int> maximum_sample(std::span<const int> samples);
