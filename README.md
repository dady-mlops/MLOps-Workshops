# MLOps-Workshops

## Перелік воркшопів 
- [Використання Ray](Ray) - July 16, 2024
- [Розгортання та моніторинг ML/LLM моделей](Deploy_and_Observability) - August 20, 2024
- [AI від досліджень до деплою у продакшн (благодійний івент на підтримку Охматдиту)](From_Research_to_Production) - August 27, 2024
- [CI/CD для Machine Learning, Large Language Models та AI Agents](CI_CD) - April 2, 2025

##Налаштування

Використання віртуального середовища Python
```
python -m venv .venv
source .venv/bin/activate
```

Використання віртуального середовища Python з певною версією 
```
pyenv install 3.10
pyenv shell 3.10
python -m venv .venv
source .venv/bin/activate
```

Налаштування AWS
```
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
aws configure
pip install boto3
```

Створення локального Kubernetes кластеру
```
https://www.docker.com/products/docker-desktop/
brew install helm
brew install kubectl or brew install kubectl
brew install minikube

minikube start --driver=docker
```

https://k8slens.dev/

Видалення локального Kubernetes кластеру
```
minikube delete --all
```