from setuptools import setup, find_packages

setup(
    name="ini_class_parser",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
        ],
    },
)
