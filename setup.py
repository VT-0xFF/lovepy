from setuptools import setup, find_packages

setup(
    name="lovepy",
    version="1.0.0",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    author="VT",
    description="A lovense control link library to connect to lovense links",
    license='GPLv3',
    license_files=['LICENSE'],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10.9',
)
