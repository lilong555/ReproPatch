#define JSON_DIAGNOSTICS 1
#include <nlohmann/json.hpp>

int main()
{
    using nlohmann::json;

    json parent = json::object();
    parent["root"] = "root_str";

    json child = json::object();
    child["prop1"] = "prop1_value";
    parent.insert(child.begin(), child.end());

    const json copied(parent);
    return copied.dump() == R"({"prop1":"prop1_value","root":"root_str"})" ? 0 : 1;
}
