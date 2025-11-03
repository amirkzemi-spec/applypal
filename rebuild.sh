#!/bin/bash
pip install --upgrade pip
pip uninstall -y python-telegram-bot telegram
pip install python-telegram-bot==20.8
pip install -r requirements.txt --no-cache-dir
