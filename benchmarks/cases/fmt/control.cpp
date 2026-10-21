#include <fmt/format.h>
#include <array>
#include <fmt/ranges.h>
#include <string>
int main(int argc, char**) {
  if (argc == 1) return fmt::format("{} {}", 42, "ok") != "42 ok";
  std::array<int, 3> a{1, 2, 3};
  return fmt::format("{}", a) != "[1, 2, 3]" ||
    fmt::format("{:*>12a}", 1.0) != "******0x1p+0" ||
    fmt::format("{:.2f}", -1.25) != "-1.25";
}
