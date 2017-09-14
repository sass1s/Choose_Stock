# -*- coding: utf-8 -*-
from django.db import models


# Create your models here.
class News(models.Model):  # 股票消息面数据库
    name = models.CharField(max_length=128, unique=True)  # 新闻的标题,必须是唯一的
    url = models.URLField()  # 新闻的网络连接
    content = models.TextField()  # 新闻的内容
    published_time = models.DateTimeField()  # 新闻发表的时间
    origin_from = models.CharField(max_length=64)  # 新闻的来源
    flag_pn = models.IntegerField(default=1)  # 记录新闻的利好还是利空,1为利好,0为利空,-1为无价值

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'news'


class Name_Id(models.Model):  # 股票代码及名称
    stock_name = models.CharField(max_length=16, unique=True)  # 股票名称,唯一
    stock_id = models.CharField(max_length=8, unique=True)  # 股票代码, 唯一

    def __str__(self):
        return '{}-{}'.format(self.stock_name, self.stock_id)


class KmeansData(models.Model):
    stock_name = models.CharField(max_length=16)  # 股票名称
    stock_id = models.CharField(max_length=8)  # 股票代码
    stock_date = models.DateField()  # 交易日期
    price_open = models.CharField(max_length=10)  # 开盘价
    price_high = models.CharField(max_length=8)  # 最高价
    price_low = models.CharField(max_length=8)  # 最低价
    price_close = models.CharField(max_length=8)  # 收盘价
    stock_volumn = models.CharField(max_length=20)  # 成交量
    stock_id_date = models.CharField(max_length=20, unique=True)  # 重要,由股票代码及交易日期组成的字段,判断信息是否唯一的标识.


class CashFlowData(models.Model):
    stock_name = models.CharField(max_length=16)  # 股票名称
    stock_id = models.CharField(max_length=8)  # 股票代码
    stock_date = models.DateField()  # 交易日期
    price_close = models.CharField(max_length=8)  # 收盘价
    var_degree = models.CharField(max_length=8)  # 股票的涨跌幅度,如-3.2%
    maincash_in = models.CharField(max_length=8)  # 主力净流入
    maincash_in_rate = models.CharField(max_length=8)  # 主力净占比
    join_degree = models.CharField(max_length=8)  # 机构参与度
    control_type = models.CharField(max_length=8)  # 控盘类型:不控盘,轻度控盘,中度控盘,完全控盘
    main_cost = models.CharField(max_length=8)  # 主力成本
    stock_id_date = models.CharField(max_length=20, unique=True)


class KStockList(models.Model):
    stock_kid_yes = models.CharField(max_length=300)  # 保留昨日的K线图股票推荐
    stock_kid_now = models.CharField(max_length=300)  # 保留今日的K线图股票推荐
    kflag = models.CharField(max_length=4)  # 是否已更新的状态,0表示未更新,1表示更新


class CStockList(models.Model):
    stock_cid_yes = models.CharField(max_length=300)  # 保留昨日的资金流图股票推荐
    stock_cid_now = models.CharField(max_length=300)  # 保留今日的资金流图股票推荐
    cflag = models.CharField(max_length=4)


class VisitData(models.Model):
    ip_address = models.CharField(max_length=16)  # ip地址
    visit_time = models.DateTimeField()  # 访问时间
    visit_page = models.CharField(max_length=20)  # 访问页面
    visit_device = models.CharField(max_length=300)  # 访问设备
