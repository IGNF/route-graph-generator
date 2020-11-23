FROM centos:7.8.2003

ENV PYTHON_VERSION "3.6.5"
ENV HOME=/home

RUN yum install -y \
  make \
  openssl-devel bzip2-devel \
  postgresql-devel wget \
  yum-utils centos-release-scl epel-release

RUN yum install -y cmake3 \
  && yum install -y python36 python36-setuptools && easy_install-3.6 pip

RUN pip3 install 'psycopg2-binary==2.8.5' 'sqlparse==0.2.4' 'lxml==4.3.1' 'paramiko==2.4.2' 'scp==0.13.2'

### Pour la conversion osm vers osrm
# Dépendances
RUN yum-config-manager --enable rhel-server-rhscl-7-rpms

# Un compilateur pour Boost et GCC 6: gcc-c++
# Pour GCC 6.3.0 afin de compiler OSRM: GMP 4.2+, MPFR 2.4.0+ and MPC 0.8.0+
# Pour OSRM: boost 1.65.1; expat 2.2.0; lua 5.2.4; bzip2 1.0.6; tbb 
# Pour Boost: openmpi-devel python-devel
# Pour LUA: readline-devel
RUN yum -y install git unzip gcc-c++ gmp-devel \
    mpfr-devel libmpc-devel flex flex-devel cmake3 zlib zlib-devel tbb tbb-devel \
    expat expat-devel lbzip2 bzip2-devel openmpi-devel python-devel readline-devel

### Installation de gcc 6.2.0 pour compiler OSRM 
WORKDIR /home/docker/gcc
# TODO: essayer avec gcc 6.3.1 
RUN git clone -b releases/gcc-6.3.0 --depth 1 https://gcc.gnu.org/git/gcc.git
# C'est volontairement en dehors des sources de gcc (voir documentation)
WORKDIR /home/docker/gcc/objdir
# https://gibsonic.org/tools/2019/08/08/gcc_building.html
RUN /home/docker/gcc/gcc/configure --prefix=$(pwd) --disable-multilib --disable-werror --enable-languages=c,c++ && make -j4 && make DESTDIR=/opt/gcc-6/ install
### Installation des dépendances de OSRM
# https://github.com/Project-OSRM/osrm-backend/wiki/Building-OSRM

# Installation de boost 1.65.1 (boost, filesystem, iostreams, program-options, regex, test, date-time, thread, system)
WORKDIR /home/docker/boost 
RUN wget https://dl.bintray.com/boostorg/release/1.65.1/source/boost_1_65_1.tar.gz && tar -xzf boost_1_65_1.tar.gz
WORKDIR /home/docker/boost/boost_1_65_1
RUN ./bootstrap.sh && ./b2 install 
# Installation de lua 5.2.4
WORKDIR /home/docker/lua
RUN wget http://www.lua.org/ftp/lua-5.2.4.tar.gz && tar zxf lua-5.2.4.tar.gz
WORKDIR /home/docker/lua/lua-5.2.4
RUN make linux test && make linux install 

### Installation de OSRM pour utiliser la libosrm dans Road2
# https://github.com/Project-OSRM/osrm-backend
# https://github.com/Project-OSRM/osrm-backend/blob/master/docs/nodejs/api.md
# https://github.com/door2door-io/osrm-express-server-demo
# https://github.com/Project-OSRM/osrm-backend/blob/master/CMakeLists.txt
WORKDIR /home/docker/osrm
RUN wget https://github.com/Project-OSRM/osrm-backend/archive/v5.23.0.zip && unzip v5.23.0.zip -d ./osrm-backend
WORKDIR /home/docker/osrm/osrm-backend/osrm-backend-5.23.0/build 
# https://developers.redhat.com/blog/2015/02/05/gcc5-and-the-c11-abi/
RUN export CC=/opt/gcc-6/home/docker/gcc/objdir/bin/gcc && export CXXFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0" && cmake3 .. -DCMAKE_BUILD_TYPE=Release -DENABLE_MASON=OFF -DCMAKE_CXX_COMPILER=/opt/gcc-6/home/docker/gcc/objdir/bin/g++ && make -j4 && make install
# https://gcc.gnu.org/onlinedocs/libstdc++/faq.html#faq.how_to_set_paths
ENV LD_LIBRARY_PATH=/opt/gcc-6/home/docker/gcc/objdir/lib64:$LD_LIBRARY_PATH

RUN mkdir /usr/lib/python3.6/site-packages/r2gg
RUN mkdir /usr/lib/python3.6/site-packages/r2gg/r2gg

COPY r2gg /usr/lib/python3.6/site-packages/r2gg/r2gg
COPY setup.py /usr/lib/python3.6/site-packages/r2gg

RUN cd /usr/lib/python3.6/site-packages/r2gg && pip3 install -e .

RUN mkdir /home/docker/data/
COPY docker/centos7/config/* ./
COPY docker/centos7/config/costs_calculation_sample.json /home/docker/data/costs_calculation_sample.json
COPY docker/centos7/config/output_base.json /home/docker/data/output_base.json
COPY sql/bduni_convert.sql ./bduni_convert.sql

ENV LANG en_US.utf8

# Commandes pour lancer une génération
RUN ["chmod", "+x", "./r2gg_pipeline.sh"]

# Montage du volume pour partager les données
VOLUME ["/home/docker/data"]
