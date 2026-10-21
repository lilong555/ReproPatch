#include <fmt/format.h>
int main() {
  if (fmt::format("{:012a}", 1.0) != "0x0000001p+0") return 1;
  if (fmt::format("{:013a}", -1.0) != "-0x0000001p+0") return 2;
  if (fmt::format("{:012A}", 1.0) != "0X0000001P+0") return 3;
  return fmt::format("{:*>12a}", 1.0) != "******0x1p+0";
}
