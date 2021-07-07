FROM python:3.8-slim
RUN pip install numpy==1.19.2 pandas==1.1.3 scikit-learn==0.23.2 joblib==0.16.0
WORKDIR /code
ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" skipcache
ADD income_train.py /code/income_train.py