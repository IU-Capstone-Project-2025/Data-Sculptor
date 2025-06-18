# Data-Sculptor
An integrated IDE agent that mentors users in Machine Learning and Data Science by providing real-time educational feedback

## Features

1. Real-time syntax analysis
  
    Get instant feedback on your code quality with advanced linters.

2. Deep Syntax Validation
  
    Comprehensive code analysis using multiple linters: pylint, mypy, dodgy, pydocstyle, vulture

3. Integrated Workflow
  
    End-to-end pipeline from code editing to validation:

    - Edit code in Jupyter notebooks

    - Save with Ctrl+S → Auto-linting

4. One-Click Environment

    Fully containerized setup with Docker Compose

## 🚀 How to use

1. Clone the repository:

```bash
git clone https://github.com/IU-Capstone-Project-2025/Data-Sculptor.git
cd Data-Sculptor
```

2. Start the JupyterHub

```bash
cd deployment/uat 
docker compose up --build
```

3. Enter the container
```bash
docker exec -it <container_name_or_id> bash
```

Then:
```
mkdir -p /home/developer/.local/share/jupyter/runtime && \
chown -R developer:developer /home/developer
```

4. Login at:
   http://localhost (default port :11000)





