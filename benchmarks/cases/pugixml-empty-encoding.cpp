#include "pugixml.hpp"
int main() {
  pugi::xml_document doc;
  auto a = doc.load_buffer(nullptr, 0, pugi::parse_fragment);
  if (!a || a.encoding != pugi::encoding_utf8) return 1;
  auto b = doc.load_buffer("", 0, pugi::parse_fragment, pugi::encoding_utf16_le);
  if (!b || b.encoding != pugi::encoding_utf16_le) return 2;
  auto c = doc.load_buffer(nullptr, 0);
  return c.status != pugi::status_no_document_element || c.encoding != pugi::encoding_utf8;
}
