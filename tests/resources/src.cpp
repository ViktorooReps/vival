#include <iostream>

int inc(int x) { return x + 1; }

int main()
{
    int x;
    while (std::cin >> x) std::cout << inc(x) << " ";
}