from setuptools import setup, find_packages

setup(
    name="llm_custom_providers",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.2.11",
        "requests>=2.32.3",
    ],
    entry_points={
        "jupyter_ai.model_providers": [
            "adviser = llm_custom_providers.adviser_provider:AdviserProvider",
        ],
    },
)
