#!/usr/bin/env bash


export PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/bin

cd /root/CS/daohua_cs/s_c_stock
nohup scrapy crawl choose_stock_news &
#ls
