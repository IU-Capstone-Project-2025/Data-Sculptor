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

2. Use docker-compose to build the service

```bash
cd deployment/uat 
docker compose up --build
```
3. Open the service in browser (default port: 9000)

4. Real-time static analysis runs automatically.

5. Ctrl+S triggers heavy syntatic analysis linters.

❗️ **The connection with LLM endpoint and service's server can work only with Innopolis internal network**




