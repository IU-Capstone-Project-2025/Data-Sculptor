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

    - Press Syntactic-Analysis button and get the feedback in LSP format
    ![image](https://github.com/user-attachments/assets/a0e800d4-1de5-498c-afec-ca5dff8b8d7c)

    - Press Semantic-Analysis button and get the .md report in same directory with .ipynb
    ![image](https://github.com/user-attachments/assets/2ec28aba-7777-473e-a5f0-53c94319f9e6)


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

3. Enter the JupyterHub container
```bash
docker exec -it uat-jupyterhub bash
```

Then:
```
mkdir -p /home/developer/.local/share/jupyter/runtime && \
chown -R developer:developer /home/developer
```

❗️Exit the container before authorization in browser

4. Login at:
   http://localhost:11000


