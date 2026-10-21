#include <fmt/compile.h>
#include <fmt/ranges.h>
#include <array>
#include <list>
#include <string>
#include <tuple>
#include <map>
int main() {
  std::array<int, 3> a{1, 2, 3};
  if (fmt::format(FMT_COMPILE("array={}"), a) != "array=[1, 2, 3]") return 1;
  if (fmt::format(FMT_COMPILE("{:*>20}"), a) != "***********[1, 2, 3]") return 2;
  if (fmt::format(FMT_COMPILE("{:*>20:{}}"), a, 3) != "*****[  1,   2,   3]") return 3;
  std::list<char> out;
  fmt::format_to(std::back_inserter(out), FMT_COMPILE("{:*>20}"), a);
  if (std::string(out.begin(), out.end()) != "***********[1, 2, 3]") return 4;
  if (fmt::format(FMT_COMPILE("{}"), std::make_tuple(1, 2)) != "(1, 2)") return 5;
  return fmt::format(FMT_COMPILE("{}"), std::map<int, int>{{1, 2}}) != "{1: 2}";
}
