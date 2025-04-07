from setuptools import setup, find_packages

setup(
    name="promptql-mcp-server",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="MCP server for PromptQL",
    long_description = open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/promptql-mcp-server",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "mcp>=0.5.0",
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "promptql-mcp=promptql_mcp_server.__main__:main",
        ],
    },
)