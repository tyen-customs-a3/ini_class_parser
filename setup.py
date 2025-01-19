from setuptools import setup, find_packages

setup(
    name="mission_scanner",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    install_requires=[],
    entry_points={
        'console_scripts': [
            'mission-scanner=mission_scanner.cli:main',
        ],
    },
    url="https://github.com/tyen-customs-a3/mission_scanner",
    author="Tom Campbell",
    description="Mission file analyzer for Arma missions",
)
