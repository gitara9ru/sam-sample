FROM public.ecr.aws/lambda/python:3.9
ENV PYTHONPATH /var/task
COPY requirements.txt ./
RUN python3.9 -m pip install -r requirements.txt -t .
COPY app.py ./
COPY app_utils/ ./app_utils/

CMD ["app.lambda_handler"]
