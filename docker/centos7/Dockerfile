FROM centos:7.5.1804

ARG proxy=""

ENV http_proxy=$proxy https_proxy=$proxy HTTP_PROXY=$proxy HTTPS_PROXY=$proxy
ENV PYTHON_VERSION "3.6.5"
ENV HOME=/home

RUN yum install -y \
  make \
  openssl-devel bzip2-devel \
  postgresql-devel wget \
  yum-utils centos-release-scl epel-release

RUN yum install -y cmake3 \
  && yum install -y python36 python36-setuptools && easy_install-3.6 pip

RUN pip3 install 'psycopg2==2.7.6.1' 'sqlparse==0.2.4' 'lxml==4.3.1' 'paramiko==2.4.2' 'scp==0.13.2'

### Pour la conversion osm vers osrm
# Dépendances
RUN yum-config-manager --enable rhel-server-rhscl-7-rpms
RUN yum install -y devtoolset-8

WORKDIR /home/docker

### Installation de OSRM pour utiliser la libosrm dans Road2
# https://github.com/Project-OSRM/osrm-backend
# https://github.com/Project-OSRM/osrm-backend/blob/master/docs/nodejs/api.md
# https://github.com/door2door-io/osrm-express-server-demo
# https://github.com/Project-OSRM/osrm-backend/blob/master/CMakeLists.txt
WORKDIR /home/docker/osrm
RUN wget https://github.com/Project-OSRM/osrm-backend/archive/v5.20.0.zip
RUN unzip v5.20.0.zip -d ./osrm-backend
WORKDIR /home/docker/osrm/osrm-backend/osrm-backend-5.20.0/build
RUN scl enable devtoolset-8 bash && export CC=/opt/rh/devtoolset-8/root/usr/bin/gcc && cmake3 .. -DCMAKE_BUILD_TYPE=Release -DENABLE_MASON=ON -DCMAKE_CXX_COMPILER=/opt/rh/devtoolset-8/root/usr/bin/g++ && make && make install


ENV PATH "/usr/local/bin:${PATH}"

RUN mkdir /usr/lib/python3.6/site-packages/r2gg
RUN mkdir /usr/lib/python3.6/site-packages/r2gg/r2gg

COPY r2gg /usr/lib/python3.6/site-packages/r2gg/r2gg
COPY setup.py /usr/lib/python3.6/site-packages/r2gg

RUN cd /usr/lib/python3.6/site-packages/r2gg && pip3 install -e .

RUN mkdir /home/docker/data/
COPY docker/centos7/config/* /home/docker/data/
COPY sql/bduni_convert.sql ./bduni_convert.sql

ENV LANG en_US.utf8

# Commandes pour lancer une génération
RUN ["chmod", "+x", "./r2gg_pipeline.sh"]

# Montage du volume pour partager les données
VOLUME ["/home/docker/data"]
