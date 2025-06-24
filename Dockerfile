FROM tiangolo/uwsgi-nginx-flask:python3.10

# Copy requirements
COPY requirements.txt /tmp/

# Install dependencies
RUN pip install -r /tmp/requirements.txt
RUN pip install flask_sqlalchemy cryptography

# Copy app code
COPY . .

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser

# Set environment variables to drop privileges
ENV UWSGI_UID=appuser
ENV UWSGI_GID=appuser

# Switch to non-root user
USER appuser
