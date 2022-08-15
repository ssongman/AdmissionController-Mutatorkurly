FROM python:3.7
RUN pip install flask
RUN pip install jsonpatch
WORKDIR /app
ADD mutatorkurly.py .
CMD ["python", "-u", "mutatorkurly.py"]
