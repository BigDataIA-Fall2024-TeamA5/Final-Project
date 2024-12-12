from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CppExtension

setup(
    name='custom_extension',
    ext_modules=[
        CppExtension(
            name='custom_extension',
            sources=['source.cpp'],  # Ensure this matches the actual file path
        )
    ],
    cmdclass={
        'build_ext': BuildExtension
    }
)