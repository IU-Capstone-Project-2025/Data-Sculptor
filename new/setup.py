from setuptools import setup, find_packages

setup(
    name="llm_custom_providers",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.2.11",
        "requests>=2.32.3",
        "jupyter-ai>=2.0.0",
        "jupyter-ai-magics>=2.0.0",
        "jupyter-server>=2.0.0",
        "tornado>=6.0.0",
    ],
    entry_points={
        "jupyter_ai.model_providers": [
            "adviser = llm_custom_providers.adviser_provider:AdviserProvider",
        ],
        "jupyter_server.extension": [
            "llm_custom_providers = llm_custom_providers:_jupyter_server_extension_points",
        ],
    },
    data_files=[
        # Frontend extension
        ("share/jupyter/nbextensions/jupyter_ai_context", [
            "llm_custom_providers/static/frontend_extension.js",
        ]),
        # Extension configuration
        ("etc/jupyter/jupyter_notebook_config.d", [
            "jupyter-config/jupyter_notebook_config.d/jupyter_ai_context.json",
        ]),
        ("etc/jupyter/jupyter_server_config.d", [
            "jupyter-config/jupyter_server_config.d/jupyter_ai_context.json",
        ]),
    ],
    include_package_data=True,
    python_requires=">=3.8",
)