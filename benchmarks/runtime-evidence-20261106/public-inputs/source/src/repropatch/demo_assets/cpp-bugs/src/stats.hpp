#pragma once
#include <optional>
#include <span>

// 返回最大样本值；空序列返回空值。
std::optional<int> maximum_sample(std::span<const int> samples);
