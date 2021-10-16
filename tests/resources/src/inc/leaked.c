#include <stdio.h>
#include <stdlib.h>

int inc(int x) { return x + 1; }

int main()
{
    int x;
    int *leak = malloc(sizeof(int));
    while (scanf("%d", leak) == 1) printf("%d ", inc(*leak));
}