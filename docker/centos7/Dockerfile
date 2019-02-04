FROM centos:7.5.1804

ARG proxy="http://proxy.ign.fr:3128/"

ENV http_proxy=$proxy https_proxy=$proxy HTTP_PROXY=$proxy HTTPS_PROXY=$proxy
ENV PYTHON_VERSION "3.6.5"
ENV HOME=/home

RUN yum install -y \
  wget \
  gcc make \
  zlib-dev openssl-devel bzip2-devel \
  postgresql-devel git

RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
  && tar xvf Python-${PYTHON_VERSION}.tgz \
  && cd Python-${PYTHON_VERSION} \
  && ./configure --prefix=/usr/local \
  && NPROC=$(grep -c ^processor /proc/cpuinfo 2>/dev/null || 1) \
  && make -j${NPROC} \
  && make altinstall -j${NPROC} \
  && cd / \
  && rm -rf Python-${PYTHON_VERSION}*

RUN git clone --depth=1 --branch=2_7_6_1  https://github.com/psycopg/psycopg2.git \
  && cd psycopg2 \
  && python3.6 setup.py build \
  && python3.6 setup.py install

RUN git clone --depth=1 --branch=0.2.4  https://github.com/andialbrecht/sqlparse.git \
  && cd sqlparse \
  && python3.6 setup.py install

RUN yum install python-lxml -y

ENV PATH "/usr/local/bin:${PATH}"

WORKDIR /home

ENTRYPOINT ["python3.6"]
