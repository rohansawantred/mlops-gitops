# OpenShift-friendly non-root pipeline / inference image
FROM registry.access.redhat.com/ubi9/python-311:latest

USER 0
WORKDIR /opt/fraud

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY training ./training
COPY pipelines ./pipelines
COPY feast ./feast
COPY inference ./inference
COPY samples ./samples
COPY pyproject.toml .

RUN chown -R 1001:0 /opt/fraud && chmod -R g=u /opt/fraud
USER 1001

ENV PYTHONPATH=/opt/fraud \
    FEAST_REPO_PATH=/opt/fraud/feast/feature_repo \
    HOME=/opt/fraud

EXPOSE 8080
CMD ["uvicorn", "inference.app:app", "--host", "0.0.0.0", "--port", "8080"]
