"""
Setup script for recon-again
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="recon-again",
    version="0.1.0",
    description="AI-powered reconnaissance framework with OpenRouter integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="recon-again team",
    url="https://github.com/recon-again/recon-again",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "neo4j>=5.0.0",
        "asyncio",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
        "tools": [
            "sublist3r",
            "dnsrecon",
            "waybackpy",
        ]
    },
    entry_points={
        "console_scripts": [
            "recon-again=recon_again.cli:cli_entry",
            "recon-again-init-db=recon_again.database.init_db:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

