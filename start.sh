#!/bin/bash
gunicorn -c deploy/gunicorn_conf.py main:app