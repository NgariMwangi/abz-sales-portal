FROM tiangolo/uwsgi-nginx-flask:python3.10

# copy over our requirements.txt file
COPY requirements.txt /tmp/

ENV OAUTHLIB_INSECURE_TRANSPORT=0

# upgrade pip and install required python packages
# RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt
RUN pip install flask_sqlalchemy
RUN pip install cryptography


# copy over our org code
COPY . .