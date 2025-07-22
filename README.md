# Data-Sculptor
An integrated IDE agent that mentors users in Machine Learning and Data Science by providing real-time educational feedback

## Features

1. Real-time syntax analysis
  
    Get instant feedback on your code quality with advanced linters.

2. Deep Syntax Validation
  
    Comprehensive code analysis using multiple linters: ruff, pylint, vulture, bandit, ml-smell-detector

3. Integrated Workflow
  
    End-to-end pipeline from code editing to validation:

    - Edit code in Jupyter notebooks

    - Press Syntactic-Analysis button and get the feedback in LSP format
    ![image](https://github.com/user-attachments/assets/a0e800d4-1de5-498c-afec-ca5dff8b8d7c)

    - Press Semantic-Analysis button and get the .md report in same directory with .ipynb and localized feedback as comments in your notebook
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
cd deployment
docker compose -p uat --env-file uat.env up --build
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
   http://localhost:52152

## Environment variables

You should change some variables before using this application:

1. Go to the `.env` file and change all strings marked with `<>` signs. Write your secret values here
2. Setup Keycloak:
	- If you dont have any KeyCloak config:
		- Run the application. Enter admin panel of **KeyCloak** at **\<yourdomain\>:53010** and enter your admin credentials
		-  Create new realm and setup it
	- If you do, just import **KeyCloak** settings (*import/export  topic is below*)
3. Copy your secret **realm's client key** secret key and paste it to *KEYCLOAK_AUTH_CLIENT_SECRET* in `.env` file


## Exporting/Importing KeyCloak settings
For easy setup and fast setup you may export/import settings. All KeyCloak configuration files are stored in the following location:
```bash
Data-Sculptor
	resources
	│   ├── config
	│   │   ├── jupyterhub
	│   │   │   ...
	│   │   ├── keycloak
	│   │   │   ├── export_data
	│   │   │   └── import_data
```

**To export** existing setting use the command below. It exports realm's settings. If `--realm` arg is not set, KeyCloak exports all existing realms
```bash
docker exec dev-keycloak /opt/keycloak/bin/kc.sh export --dir /opt/keycloak/data/export --realm <REALM-NAME> --users realm_file
```

**To import** an existing config use this command. Specify `.json` file with realm settings you want to create/override:
```bash
docker exec dev-keycloak /opt/keycloak/bin/kc.sh import --dir /opt/keycloak/data/import --file <REALM-FILENAME.json> --users realm_file
```