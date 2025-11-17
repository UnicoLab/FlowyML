"""
Setup file for Flowy package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="flowy",
    version="0.1.0",
    author="Flowy Team",
    author_email="team@flowy.ai",
    description="Next-Generation ML Pipeline Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/flowy/flowy",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
    ],
    extras_require={
        "pytorch": ["torch>=2.0.0"],
        "tensorflow": ["tensorflow>=2.12.0"],
        "sklearn": ["scikit-learn>=1.0.0"],
        "all": [
            "torch>=2.0.0",
            "tensorflow>=2.12.0",
            "scikit-learn>=1.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.990",
        ],
    },
    entry_points={
        "console_scripts": [
            "flowy=flowy.cli.main:main",
        ],
    },
)
