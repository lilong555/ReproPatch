#include "tinyxml2.h"
int main() {
  tinyxml2::XMLDocument doc;
  doc.DeleteNode(nullptr);
  if (doc.Parse("<root/>")) return 1;
  auto* root = doc.RootElement();
  doc.DeleteNode(nullptr);
  return doc.RootElement() != root;
}
