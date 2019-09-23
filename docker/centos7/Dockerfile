FROM centos:7.5.1804

ARG proxy=""

ENV http_proxy=$proxy https_proxy=$proxy HTTP_PROXY=$proxy HTTPS_PROXY=$proxy
ENV PYTHON_VERSION "3.6.5"
ENV HOME=/home

RUN yum install -y \
  make \
  openssl-devel bzip2-devel \
  postgresql-devel git \
  yum-utils centos-release-scl epel-release

RUN yum install -y cmake3 \
  && yum install -y python36 python36-setuptools && easy_install-3.6 pip

RUN pip3 install 'psycopg2==2.7.6.1' 'sqlparse==0.2.4' 'lxml==4.3.1' 'paramiko==2.4.2' 'scp==0.13.2'

### Pour la conversion osm vers osrm
# Dépendances
RUN yum-config-manager --enable rhel-server-rhscl-7-rpms
RUN yum install -y devtoolset-8

WORKDIR /home/docker

RUN git clone --depth=1 --branch=v5.20.0 https://github.com/Project-OSRM/osrm-backend.git \
  && cd osrm-backend \
  && mkdir -p build \
  && cd build \
  && scl enable devtoolset-8 bash && export CC=/opt/rh/devtoolset-8/root/usr/bin/gcc \
  && cmake3 .. -DCMAKE_BUILD_TYPE=Release -DENABLE_MASON=ON -DCMAKE_CXX_COMPILER=/opt/rh/devtoolset-8/root/usr/bin/g++ \
  && make && make install

ENV PATH "/usr/local/bin:${PATH}"

RUN mkdir /usr/lib/python3.6/site-packages/r2gg
RUN mkdir /usr/lib/python3.6/site-packages/r2gg/r2gg

COPY r2gg /usr/lib/python3.6/site-packages/r2gg/r2gg
COPY setup.py /usr/lib/python3.6/site-packages/r2gg

RUN cd /usr/lib/python3.6/site-packages/r2gg && pip3 install -e .

RUN mkdir /home/docker/data/
COPY docker/centos7/config/* ./
COPY docker/centos7/config/bduniv2_avec_sens_vitesse_fixe.lua /home/docker/data/bduniv2_avec_sens_vitesse_fixe.lua
COPY docker/centos7/config/bduniv2_distance.lua /home/docker/data/bduniv2_distance.lua
COPY docker/centos7/config/costs_calculation_sample.json /home/docker/data/costs_calculation_sample.json
COPY docker/centos7/config/output_base.json /home/docker/data/output_base.json
COPY sql/bduni_convert.sql ./bduni_convert.sql

ENV LANG en_US.utf8

# Commandes pour lancer une génération
RUN ["chmod", "+x", "./r2gg_pipeline.sh"]

# Montage du volume pour partager les données
VOLUME ["/home/docker/data"]
