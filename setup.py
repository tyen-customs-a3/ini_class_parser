from setuptools import setup, find_packages

setup(
    name="ini_class_parser",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    install_requires=[],
    author="Tom Campbell",
    description="INI Class Parser for configuration files",
)
