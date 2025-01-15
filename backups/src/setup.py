"""Setup script for the project"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="quantum-ai-system",
    version="0.1.0",
    author="Him",
    author_email="him@example.com",
    description="Advanced AI system with quantum-inspired capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/him/quantum-ai-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "aiohttp>=3.8.0",
        "websockets>=10.0",
        "mitmproxy>=9.0.0",
        "cryptography>=41.0.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "numpy>=1.21.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.0.0",
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.22.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.11.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.1.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "mypy>=1.4.0",
        "pylint>=2.17.0",
    ],
    extras_require={
        "dev": [
            "black",
            "isort",
            "mypy",
            "pylint",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "sphinx-autodoc-typehints>=1.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "quantum-ai=main:main",
        ],
    },
)
