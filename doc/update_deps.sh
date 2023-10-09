#!/bin/bash

# updates requirements.txt by installing the latest requirements into a
# temporary virtualenv

REQUIREMENTS="Sphinx sphinx-rtd-theme"

###

set -eu

ENV=$(mktemp -d env.XXXXX)
python -m venv $ENV
source $ENV/bin/activate

pip install $REQUIREMENTS
pip freeze | grep -v '^-' > requirements.txt

deactivate
rm -r $ENV
