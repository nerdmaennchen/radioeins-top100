# a super simple crawler for the top-100 show on radioeins

The crawler fetches jury votes from [here](https://www.radioeins.de/musik/die-100-besten-2019) and accumulates the votes to generate the ranking by hand.

how to get it running:
~~~
virtualenv --python=python3 venv
. venv/bin/activate
pip install -r requirements.txt
python fetch.py [list] # where [list] is any list they did... e.g. staedtesongs
~~~
