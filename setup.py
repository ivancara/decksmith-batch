"""
DeckSmith Batch Processing - Setup Configuration
================================================

Setup script para instalação e configuração do sistema.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="decksmith-batch",
    version="1.0.0",
    author="DeckSmith Team",
    author_email="team@decksmith.com",
    description="Sistema de processamento em lote para análise de dados MTG",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/decksmith/decksmith-batch",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "flake8>=6.0.0",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "sentry-sdk>=1.32.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "decksmith-batch=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "decksmith-batch": ["*.sql", "*.yaml", "*.json"],
    },
)