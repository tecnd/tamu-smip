The dashboard application is located in plot.py, and should be deployed with a WSGI server such as gunicorn or waitress.

First, install the required dependencies. A conda environment file is provided in environment.yml so a clean environment can be created with

    conda env create -f environment.yml

Note that Python 3.8 is required.
Next, install the MATLAB engine for Python. MATLAB R2021A is required.
Navigate to where MATLAB is installed. Under extern/engines/python, run the install script with

    python setup.py install

Finally, start the server. For example,

    gunicorn plot:app.server -b 0.0.0.0:8000 -w 4

will start gunicorn on port 8000 with 4 workers.