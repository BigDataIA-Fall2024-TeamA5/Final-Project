FROM apache/airflow:2.10.3

# Switch to airflow user for pip installation
USER airflow

# Copy and install requirements
COPY --chown=airflow:airflow requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt