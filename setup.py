from setuptools import setup, find_packages

setup(
    name="lovepy",
    version="1.0.0",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    author="VT",
    description="A lovense control link library to connect to lovense links",
)
