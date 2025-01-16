"""Neural Fabric Extended (NFX) Setup

High-performance neural processing framework.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nfx",
    version="0.1.0",
    author="NFX Team",
    author_email="team@nfx.dev",
    description="High-performance neural processing framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nfx-team/nfx",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "click>=8.0.0",
        "pyobjc-framework-Metal>=8.0; platform_system=='Darwin'",
        "pyobjc-framework-MetalPerformanceShaders>=8.0; platform_system=='Darwin'",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "mypy>=0.900",
            "pylint>=2.12.0",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "sphinx-click>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nfx=nfx.cli.main:cli",
        ],
    },
)
