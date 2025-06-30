from setuptools import setup



setup(
    name="pylsp-bandit",
    version="0.1.0",
    description="Pylsp plugin for utilizing Bandit",
    author="Aziz",
    py_modules=["pylsp_bandit"],
    install_requires=["python-lsp-server", "bandit"],
    entry_points={"pylsp": ["bandit = pylsp_bandit"]},
)
