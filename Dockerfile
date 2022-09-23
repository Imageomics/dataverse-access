FROM python:3.10-buster
LABEL "org.opencontainers.image.authors"="John Bradley <john.bradley@duke.edu>"
LABEL "org.opencontainers.image.description"="Tool to upload and download files from a Dataverse instance"
ADD . /src
RUN cd /src && python setup.py install
CMD dva --help
