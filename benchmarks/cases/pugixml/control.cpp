#include "pugixml.hpp"
#include <cstring>
int main(int argc, char**) {
  pugi::xml_document doc;
  if (!doc.load_string("<root a='42'><child>text</child></root>")) return 1;
  if (argc == 1) return doc.child("root").attribute("a").as_int() != 42;
  pugi::xpath_variable_set original;
  original.set("s", "hello"); original.set("n", 42.0); original.set("b", true);
  pugi::xpath_variable_set copy(original);
  original.set("s", "changed");
  return std::strcmp(copy.get("s")->get_string(), "hello") ||
    copy.get("n")->get_number() != 42.0 || !copy.get("b")->get_boolean() ||
    doc.select_node("/root/child").node().text().as_string()[0] != 't';
}
