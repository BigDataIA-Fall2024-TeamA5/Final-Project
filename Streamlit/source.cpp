#include <torch/extension.h>

// Example function
int add(int a, int b) {
    return a + b;
}

// Register the function
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("add", &add, "A function that adds two numbers");
}