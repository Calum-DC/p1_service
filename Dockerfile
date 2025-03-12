FROM python:3.12-slim

ENV TEAMS_WEBHOOK=""
ENV SQS_P1_URL=""
ENV AWS_REGION=""
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""


WORKDIR /p1_service
COPY . /p1_service
RUN pip install -r requirements.txt
EXPOSE 8001
CMD ["gunicorn", "--bind","0.0.0.0:8001", "main:app"]
