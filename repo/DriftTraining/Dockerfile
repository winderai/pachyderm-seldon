FROM python:3.8-slim
RUN pip install numpy==1.19.2 pandas==1.1.3
RUN apt-get update
RUN apt-get install gcc -y
RUN apt-get clean
RUN apt install gcc python3-dev python3-pip libxml2-dev libxslt1-dev zlib1g-dev g++ -y
RUN pip install tensorflow>=2.0.0
RUN apt update -y
RUN apt install libgl1-mesa-glx -y
RUN pip install alibi-detect==0.4.3
WORKDIR /code
ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" skipcache
ADD drift_train.py /code/drift_train.py