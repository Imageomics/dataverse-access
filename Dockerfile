FROM python:3.10-buster
ADD requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt
ADD dv.py /src/dv.py
CMD python /src/dv.py --help
