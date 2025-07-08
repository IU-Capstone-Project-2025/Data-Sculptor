from setuptools import setup

setup(
    name="pylsp-vulture",
    version="0.1.0",
    description="Pylsp plugin for utilizing Vulture",
    author="Aziz",
    py_modules=["pylsp_vulture"],
    install_requires=["python-lsp-server", "vulture"],
    entry_points={"pylsp": ["vulture = pylsp_vulture"]},
)
