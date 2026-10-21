#include "pugixml.hpp"
#include <cstring>
int main() {
  pugi::xpath_variable_set original;
  if (!original.add("v", pugi::xpath_type_string)) return 1;
  pugi::xpath_variable_set copy(original);
  if (!copy.get("v") || std::strcmp(copy.get("v")->get_string(), "")) return 2;
  pugi::xpath_variable_set assigned;
  assigned.set("old", 7.0);
  assigned = original;
  return !assigned.get("v") || assigned.get("old") ||
    std::strcmp(assigned.get("v")->get_string(), "");
}
