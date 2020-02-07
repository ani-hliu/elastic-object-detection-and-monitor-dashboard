#!/bin/sh
mysql -u root "-pece1779pass" ece1779 < app/setup.sql
. venv/bin/activate
pip install .
gunicorn -w 4 -b 127.0.0.1:8000 wsgi:webapp
