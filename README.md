# Data-Sculptor
An integrated IDE agent that mentors users in Machine Learning and Data Science by providing real-time educational feedback

## 🚀 How to use

Clone the repository:

```bash
git clone https://github.com/IU-Capstone-Project-2025/Data-Sculptor.git
cd Data-Sculptor
```

2. Use docker-compose to build the service

```bash
cd deployment/dev 
docker-compose up --build
```
3. Open the service in browser (default port: 9000)

4. Login and check the functionality by running all cells of the .ipynb notebook([authorization data](https://strategic-control.kaiten.ru/documents/d/c3e7daa4-1678-4e99-839b-6caee4383234))

    The notebook uses two components:
    
      - `%load_ext sendCode` — loads a custom Jupyter extension that connects the validation mechanism to backend microservices.
    
      - `%%LLM_Validation <path_to_file>` — a magic cell that sends the code or the file(both of them are usable) for validation to the LLM via the backend service. The path specifies which file to send for validation.

5. As a result you will get the `response.md` file in 5-10 seconds after running cell with magic method

❗️ **The connection with LLM endpoint and service's server can work only with Innopolis internal network**






