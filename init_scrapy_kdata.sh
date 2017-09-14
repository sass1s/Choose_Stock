#!/usr/bin/env bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/bin

cd /root/CS/daohua_cs/KmeansData

nohup scrapy crawl eachday_kdata &
