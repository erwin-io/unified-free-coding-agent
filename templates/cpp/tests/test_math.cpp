#include "math.hpp"
#include <iostream>

int main() {
    if (agent::add(2, 3) != 5 || agent::add(-1, 1) != 0) {
        std::cerr << "Math tests failed\n";
        return 1;
    }
    std::cout << "Math tests passed\n";
    return 0;
}
