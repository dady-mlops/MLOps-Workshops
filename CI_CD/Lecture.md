# Майстерня з MLOps: CI/CD для Machine Learning, Large Language Models та AI Agents

## Зміст
 - Необхідні налаштування
 - Пайплайн тренування моделі на Ray кластері
 - Пайплайн розгортання моделі у SageMaker
 - Пайплайн розгортання AI агента



## Необхідні налаштування
1. Акаунти у AWS, GitHub, W&B, Scalr
2. Розгорнутий Ray кластер 

### Розгортання Ray Cluster
Встановлення Ray
```
pyenv install 3.10
pyenv shell 3.10
python -m venv .venv
source .venv/bin/activate
pip install boto3
pip install -U "ray[all]"
```
### AWS
Конфігурування кластера відбувається через файл `cluster-config.yaml`, який далі використовується для його запуску:
```
ray up -y CI_CD/ray/cluster-config-aws.yaml
```
Зупинка кластера 
```
ray down CI_CD/ray/cluster-config-aws.yaml
```
Приклад [ray/cluster-config-aws.yaml](cluster-config-aws.yaml) для розгортання в AWS

Щоб знайти правильний імідж для розгортання
```
aws ec2 describe-images --region us-east-2 --owners amazon \ 
--filters 'Name=name,Values=Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04) *' 'Name=state,Values=available' \
--query 'reverse(sort_by(Images, &CreationDate))[:1].ImageId' --output text
```

https://docs.amazonaws.cn/en_us/dlami/latest/devguide/what-is-dlami.html
https://docs.ray.io/en/latest/cluster/vms/references/ray-cluster-configuration.html
https://docs.ray.io/en/latest/cluster/vms/references/ray-cluster-cli.html

## Пайплайн тренування моделі на Ray кластері
Спочатку перевіряємо роботу тренування локально
```
pip install -r requirements.txt
python train_yolo.py
```
Потім перевіряємо, щоб працював запуск тренування на кластері з локального середовища
```
python run_ray_training.py
```
Тепер можемо подивитися, що у нас працює наш пайплайн у GitHub, для цього потрібно перейти в репозиторій у розділ Actions.
В ньому запускаємо пайплайн під назвою Train on Ray Cluster

Перевіряємо дані експерименту та створюємо нову версію моделі у W&B

 
## Пайплайн розгортання моделі у SageMaker
Налаштувати IAM ролі, якщо не налаштовані для роботи з S3, ECR та SageMaker

Запуск локального сервера виведення
```
python run_local_server.py
```
Тестування моделі локально
```
python test_model.py --url http://localhost:8000/invocations --image car.jpg --save my_result.jpg
```
Збірка контейнера та тестування локально
```
python build_and_test_locally.py
```
Відправка контейнера до Amazon ECR
```
python build_and_push_to_ecr.py
```
Розгортання безсерверної кінцевої точки на SageMaker
```
python deploy_serverless.py --custom-container
```
Тестування розгорнутої кінцевої точки
```
python test_model.py --endpoint https://runtime.sagemaker.us-east-2.amazonaws.com/endpoints/yolov8-serverless-endpoint/invocations --image car.jpg --save my_result.jpg
```

## Розгортання AI Агента

Для розгортання та автоматичного повторного розгортання змін потрібно налаштувати інтеграцію GitHub репозиторія з Scalr

При зміні коду у папці infra автоматично буде запускатись пайплайн у Scalr для розгортання

Також окремо є GitHub Actions під назвою Build and Push CrewAI Writer Agent to ECR для збірки контейнера агента. 
