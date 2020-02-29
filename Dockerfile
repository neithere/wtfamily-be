# https://pythonspeed.com/articles/base-image-python-docker-images/
FROM python:slim-buster AS build

LABEL maintainer="Andy Mikhaylenko <neithere@gmail.com>"

RUN apt-get update \
 && apt-get install -y git

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

COPY wtfamily/requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY ./wtfamily ./
COPY ./sample-config.yaml ./conf.yaml

CMD ["python", "app.py", "run"]
