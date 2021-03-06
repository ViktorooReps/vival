#include <iostream> 

int func(int a, int b)
{
    return a + b;
}

int main()
{
    int a, b;
    while (std::cin >> a >> b) {
        std::cout << func(a, b) << std::endl;
    }
}