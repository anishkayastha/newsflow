FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12

RUN pip install --no-cache-dir torch==2.5.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    "numpy==1.26.4" \
    "scipy==1.11.4"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models/sbert/      /opt/models/sbert/
COPY models/distilbart/ /opt/models/distilbart/

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]