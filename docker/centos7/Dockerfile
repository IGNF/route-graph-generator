FROM centos:7.5.1804

ARG proxy="http://proxy.ign.fr:3128/"

ENV http_proxy=$proxy https_proxy=$proxy HTTP_PROXY=$proxy HTTPS_PROXY=$proxy
ENV PYTHON_VERSION "3.6.5"
ENV HOME=/home

RUN yum install -y \
  wget \
  gcc make \
  zlib-dev openssl-devel bzip2-devel \
  postgresql-devel git \
  yum-utils centos-release-scl epel-release

RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
  && tar xvf Python-${PYTHON_VERSION}.tgz \
  && cd Python-${PYTHON_VERSION} \
  && ./configure --prefix=/usr/local \
  && NPROC=$(grep -c ^processor /proc/cpuinfo 2>/dev/null || 1) \
  && make -j${NPROC} \
  && make altinstall -j${NPROC} \
  && cd / \
  && rm -rf Python-${PYTHON_VERSION}*

RUN yum install -y python36-setuptools && easy_install-3.6 pip

RUN pip3 install 'psycopg2==2.7.6.1' 'sqlparse==0.2.4' 'lxml==4.3.1'

### Pour la conversion osm vers osrm
# Dépendances
RUN yum-config-manager --enable rhel-server-rhscl-7-rpms
RUN yum install -y devtoolset-6
RUN scl enable devtoolset-6 bash && yum -y install cmake3

RUN git clone --depth=1 --branch=v5.20.0 https://github.com/Project-OSRM/osrm-backend.git \
  && cd osrm-backend \
  && mkdir -p build \
  && cd build \
  && scl enable devtoolset-6 bash && export CC=/opt/rh/devtoolset-6/root/usr/bin/gcc \
  && cmake3 .. -DCMAKE_BUILD_TYPE=Release -DENABLE_MASON=ON -DCMAKE_CXX_COMPILER=/opt/rh/devtoolset-6/root/usr/bin/g++ \
  && make && make install

ENV PATH "/usr/local/bin:${PATH}"

WORKDIR /home

ENTRYPOINT ["python3.6"]
