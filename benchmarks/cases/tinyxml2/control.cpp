#include "tinyxml2.h"
#include <cstring>
int main(int argc, char**) {
  tinyxml2::XMLDocument doc;
  if (doc.Parse("<root><a/><b/></root>")) return 1;
  if (argc == 1) {
    doc.DeleteNode(doc.RootElement()->FirstChild());
    return std::strcmp(doc.RootElement()->FirstChildElement()->Name(), "b");
  }
  doc.DeleteNode(doc.NewElement("detached"));
  doc.DeleteNode(doc.RootElement());
  return doc.RootElement() != nullptr;
}
