# TODO: move to python-slim or python-slim-buster because Alpine doesn't
# support wheels, see https://pythonspeed.com/articles/base-image-python-docker-images/
FROM python:alpine AS build

LABEL maintainer="Andy Mikhaylenko <neithere@gmail.com>"

RUN apk update \
 && apk add build-base git \
 # lxml won't compile via pip :(
 && apk add libxml2-dev libxslt-dev py3-lxml

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

COPY wtfamily/requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY ./wtfamily ./
COPY ./sample-config.yaml ./conf.yaml

CMD ["python", "app.py", "run"]
