FROM python:3.11-slim

WORKDIR /scripts
COPY ./scripts/ /scripts/

COPY ./requirements.txt /scripts/
RUN pip3 install -r requirements.txt

RUN pip3 install torch==2.7.0 -f https://download.pytorch.org/whl/torch_stable.html

RUN apt-get update && apt-get install -y iputils-ping
