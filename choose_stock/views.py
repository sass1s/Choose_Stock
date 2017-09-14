# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import News, KmeansData, CashFlowData, Name_Id, KStockList, CStockList, VisitData
from datetime import datetime, timedelta
from collections import defaultdict
from django.db.models import Q
# from .select_strategy import *
from django.views.decorators.cache import cache_page

# from django.db.models import Count

now = datetime.now()  # 现在时刻,月日年时分秒
now_date = now.date()  # 现在时刻,月日年
yesterday = now + timedelta(days=-1)  # 昨天
the_day_before_yesterday = now + timedelta(days=-2)  # 前天
day_fixed_before_news = now + timedelta(days=-30)  # 10天前的消息自动从数据库中删除
day_fixed_before_kdata = now_date + timedelta(days=-121)  # 4个月前的k线图数据从数据库中删除
day_fixed_before_cdata = now_date + timedelta(days=-121)  # 4个月前的资金流数据从数据库中删除
day_fixed_before_visit = now + timedelta(days=-5)  # 5天前的访客数据从数据库中删除


# Create your views here.
def index(request):  # 处理主页的视图逻辑
    visitcount(request)
    return render(request, 'choose_stock/index.html', {})


def news(request):  # 处理消息页面的视图逻辑
    visitcount(request)
    news_dated = News.objects.filter(published_time__lte=day_fixed_before_news)  # 筛选出发布时间在特定天数前的过时消息
    news_dated.delete()  # 删除消息
    context_dict = {}  # 上下文字典
    news_today_pos = News.objects.filter(published_time__day=now.day, published_time__month=now.month,
                                         flag_pn=1).order_by(
            '-published_time')  # 提取出今日新闻利好列表,既查询,又排序,链接过滤器好
    context_dict['news_today_pos'] = news_today_pos
    news_today_neg = News.objects.filter(published_time__day=now.day, published_time__month=now.month,
                                         flag_pn=0).order_by(
            '-published_time')  # 提取今日利空新闻列表
    context_dict['news_today_neg'] = news_today_neg
    news_yes_pos = News.objects.filter(published_time__day=yesterday.day, published_time__month=yesterday.month,
                                       flag_pn=1).order_by(
            '-published_time')  # 提取昨日利好新闻列表
    context_dict['news_yes_pos'] = news_yes_pos
    news_yes_neg = News.objects.filter(published_time__day=yesterday.day, published_time__month=yesterday.month,
                                       flag_pn=0).order_by(
            '-published_time')  # 提取昨日利空新闻列表
    context_dict['news_yes_neg'] = news_yes_neg
    news_be_yes_pos = News.objects.filter(published_time__day=the_day_before_yesterday.day,
                                          published_time__month=the_day_before_yesterday.month, flag_pn=1).order_by(
            '-published_time')  # 提取前日利好新闻列表
    context_dict['news_be_yes_pos'] = news_be_yes_pos
    news_be_yes_neg = News.objects.filter(published_time__day=the_day_before_yesterday.day,
                                          published_time__month=the_day_before_yesterday.month, flag_pn=0).order_by(
            '-published_time')  # 提取前日利空新闻列表
    context_dict['news_be_yes_neg'] = news_be_yes_neg
    return render(request, 'choose_stock/news.html', context_dict)


def news_detail(request, pk):  # 显示具体新闻的视图逻辑, pk指新闻存储在mysql数据库中的id(用pk做传递参数是否存在安全隐患?)
    visitcount(request)
    context_dict = {}  # 需要传递进模板中的上下文参数字典
    try:
        news = News.objects.get(pk=pk)
        context_dict['news'] = news
    except News.DoesNotExist:
        pass
    return render(request, 'choose_stock/news_detail.html', context_dict)


# --------------------------------------------------------以下为与kmeans相关的函数
def ChangeToEchartsData_kdata(stock_id_list=['000705', '300016', '002090']):  # 将特定代码的股票数据转换为符合echarts的数据
    stocks = KmeansData.objects.filter(stock_id__in=stock_id_list).order_by('stock_date')
    # stocks = KmeansData.objects.filter(stock_id__in=['600612', '002060', '601988']).order_by('stock_date')  # 利用老凤祥测试下
    stock_seen = list({(stock.stock_id, stock.stock_name) for stock in stocks})  # 去重用,获得不重名的stock_id
    stocks_new = []  # 添加每支重构后的股票
    for id_name in stock_seen:
        stock = {}  # 重构每支股票数据
        stock['stock_id'] = id_name[0]
        stock['name'] = id_name[1]
        data = [[str(s.stock_date),
                 float(s.price_open) if float(s.price_open) > 0 else float(s.price_close),
                 float(s.price_close),
                 float(s.price_low) if float(s.price_low) > 0 else float(s.price_close),
                 float(s.price_high) if float(s.price_high) > 0 else float(s.price_close)]
                for s in stocks if s.stock_id == id_name[0]]  # 目前暂时只能用此种方式(注意列表内含列表),echarts要求,画K线图的4个数据一定为浮点数

        # 获取涨跌幅数据,目前暂用最普通的方法
        sc = [s.price_close for s in stocks if s.stock_id == id_name[0]]  # 获取所有的收盘价格
        yy = []  # 储存涨跌数据
        for x in range(len(sc) - 1):
            try:
                y = (float(sc[x + 1]) - float(sc[x])) / float(sc[x])
                yy.append('{:.2%}'.format(y))
            except Exception:
                yy.append('0.00%')
        zz = ['0.00%']
        zz.extend(yy)  # 完整的涨跌幅数据
        # zz = CashFlowData.objects.filter(stock_id=id_name[0]).order_by('stock_date').values_list('var_degree', flat=True)
        for x in range(len(zz)):
            data[x].append(zz[x])

        stock['data'] = data

        # 将涨跌的volumn分开
        volumn_data = [int(s.stock_volumn) for s in stocks if s.stock_id == id_name[0]]  # 获取该股票对应的成交量数据
        volumn_rise = []
        volumn_fall = []
        for x in range(len(data)):
            close_minus_open = data[x][2] - data[x][1]
            if close_minus_open > 0:  # 收盘价大于开盘价,此时volumn为涨,红色
                volumn_rise.append(volumn_data[x])
                volumn_fall.append('-')
            else:
                volumn_rise.append('-')
                volumn_fall.append(volumn_data[x])

        stock['volumn_rise'] = volumn_rise
        stock['volumn_fall'] = volumn_fall

        # stock['volumn'] = [int(s.stock_volumn) for s in stocks if s.stock_id == id_name[0]]
        # k += 1
        stocks_new.append(stock)
    return stocks_new


def KmeansStrategy1():  # 根据策略:跌-跌-涨-涨,最后一天下影线越短越好 选择符合要求的股票
    (*_, tradeday_0, tradeday_1, tradeday_2, tradeday_3) = KmeansData.objects.filter(stock_id='601988').dates(
            'stock_date', 'day', order='DESC')[:5]  # 提取中国银行的倒数第四个交易日,作为所有股票的倒数第四个交易日,本行第一个数字为控制变量,默认且最小为4.

    judge_3 = KmeansData.objects.filter(stock_date=tradeday_3).values_list('stock_id', 'price_open',
                                                                           'price_close')  # 获取倒数第四个交易日的股票代码,开盘价,收盘价
    stock_id_list3 = [s[0] for s in judge_3 if float(s[1]) > float(s[2])]  # 倒数第四日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    # tradeday_2 = tradeday_3 + timedelta(days=1)  # 倒数第3日
    judge_2 = KmeansData.objects.filter(stock_id__in=stock_id_list3, stock_date=tradeday_2).values_list('stock_id',
                                                                                                        'price_open',
                                                                                                        'price_close')  # 获取倒数第三个交易日的股票代码,开盘价,收盘价
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) > float(s[2])]  # 倒数第三日绿色股票代码
    # tradeday_1 = tradeday_2 + timedelta(days=1)  # 倒数第2日
    judge_1 = KmeansData.objects.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id',
                                                                                                        'price_open',
                                                                                                        'price_close',
                                                                                                        'stock_volumn')  # 倒数第二个交易日股票数据, 含成交量数据
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) < float(s[2])]  # 倒数第2日红色股票代码
    # tradeday_0 = tradeday_1 + timedelta(days=1)  # 倒数第1日
    judge_0 = KmeansData.objects.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id',
                                                                                                        'price_open',
                                                                                                        'price_close',
                                                                                                        'stock_volumn')  # 倒数第一日交易日股票数据
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码

    # 找到倒数第1日红色股票代码中,成交量较倒数第二日成交量增加的股票代码
    sid_volumn = []  # 储存通过成交量增长判定得到的股票代码
    for s_id in stock_id_list0:
        volumn1 = [int(s[3]) for s in judge_1 if s[0] == s_id]  # judge_1中的volumn
        volumn0 = [int(s[3]) for s in judge_0 if s[0] == s_id]  # judge_0中的volumn
        if volumn0[0] > volumn1[0]:
            sid_volumn.append(s_id)

    return sid_volumn


def KmeansStrategy2():  # 根据策略:跌-跌-涨,要求最后一天无下影线, 且成交量最好上升
    (*_, tradeday_0, tradeday_1, tradeday_2) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                                  order='DESC')[
                                               :3]  # 提取中国银行的倒数第三个交易日,作为所有股票的倒数第三个交易日,本行第一个数字为控制变量,默认且最小为3.
    judge_2 = KmeansData.objects.filter(stock_date=tradeday_2).values_list('stock_id', 'price_open',
                                                                           'price_close')  # 获取倒数第三个交易日的股票代码,开盘价,收盘价
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) > float(s[2])]  # 倒数第三日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    # tradeday_1 = tradeday_2 + timedelta(days=1)  # 倒数第2日----此种方法是错误的,有可能包含了周六或日
    judge_1 = KmeansData.objects.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id',
                                                                                                        'price_open',
                                                                                                        'price_close',
                                                                                                        'stock_volumn')  # 倒数第2个交易日的股票代码,开盘价,收盘价
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) > float(s[2])]  # 倒数第2日绿色股票代码
    # tradeday_0 = tradeday_1 + timedelta(days=1)  # 倒数第1日
    judge_0 = KmeansData.objects.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id',
                                                                                                        'price_open',
                                                                                                        'price_close',
                                                                                                        'price_low',
                                                                                                        'price_high',
                                                                                                        'stock_volumn')  # 倒数第一日交易日股票数据
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码

    # 找寻stock_id_list0中下影线特别短的股票
    sid_stock = []
    for sid in stock_id_list0:
        prices = [(float(s[1]), float(s[2]), float(s[3]), float(s[4]), int(s[5])) for s in judge_0 if
                  s[0] == sid]  # 获取开盘价, 收盘价,最低价,最高价
        price_open = prices[0][0]
        price_close = prices[0][1]
        price_low = prices[0][2]
        price_high = prices[0][3]
        volumn0 = prices[0][4]
        volumn1 = [int(s[3]) for s in judge_1 if s[0] == sid][0]  # 倒数第二天的成交量
        try:
            if ((price_open - price_low) / price_low < 0.001) and (
                            (price_close - price_open) / (
                                    price_high - price_low) > 0.2) and volumn0 > volumn1:  # 下影线短,开收盘价与最高低价比例的判定
                sid_stock.append(sid)
        except Exception:
            continue

    return sid_stock


def KmeansStrategy2_1(index_day=3):  # KmeansStrategy2的改进版,希望可以提高运行效率,核心为只调用一次数据库筛选
    (*_, tradeday_0, tradeday_1, tradeday_2) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                                  order='DESC')[
                                               :index_day]  # 提取中国银行的倒数第三个交易日,作为所有股票的倒数第三个交易日,本行第一个数字为控制变量,默认且最小为3.
    stocks_2 = KmeansData.objects.filter(stock_date__range=(tradeday_2, tradeday_0))  # 获取特定三个交易日的所有股票
    judge_2 = stocks_2.filter(stock_date=tradeday_2).values_list('stock_id', 'price_open',
                                                                 'price_close')  # 获取倒数第三个交易日的股票代码,开盘价,收盘价
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) > float(s[2])]  # 倒数第三日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    judge_1 = stocks_2.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close',
                                                                                              'stock_volumn')  # 倒数第2个交易日的股票代码,开盘价,收盘价
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) > float(s[2])]  # 倒数第2日绿色股票代码
    judge_0 = stocks_2.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close',
                                                                                              'price_low',
                                                                                              'price_high',
                                                                                              'stock_volumn')  # 倒数第一日交易日股票数据
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码

    # 找寻stock_id_list0中下影线特别短,成交量上涨,圆柱实体具有一定长度的股票
    sid_stock = []
    for sid in stock_id_list0:
        prices = [(float(s[1]), float(s[2]), float(s[3]), float(s[4]), int(s[5])) for s in judge_0 if
                  s[0] == sid]  # 获取开盘价, 收盘价,最低价,最高价
        price_open = prices[0][0]
        price_close = prices[0][1]
        price_low = prices[0][2]
        price_high = prices[0][3]
        volumn0 = prices[0][4]
        volumn1 = [int(s[3]) for s in judge_1 if s[0] == sid][0]  # 倒数第二天的成交量
        try:
            if ((price_open - price_low) / price_low < 0.001) and (
                            (price_close - price_open) / (
                                    price_high - price_low) > 0.2) and volumn0 > volumn1:  # 下影线短,开收盘价与最高低价比例的判定
                sid_stock.append(sid)
        except Exception:
            continue

    stocks_cash = CashFlowData.objects.filter(stock_id__in=sid_stock, stock_date=tradeday_0)  # 最新一天的资金净流入数据
    value_cash = stocks_cash.values_list('stock_id', 'maincash_in')  # 提取主力净流入数据
    value_pos_cash = [s for s in value_cash if not s[1].startswith('-')]  # 提取资金流正流入的股票
    value_Pos_cash = [s for s in value_pos_cash if s[1].endswith('万') or s[1].endswith('亿')]  # 去掉资金净流入还不足万元的股票
    num_Pos_cash = [(s[0], float(s[1][:-1])) if s[1].endswith('万') else (s[0], float(s[1][:-1]) * 10 ** 4) for s in
                    value_Pos_cash]  # 将股票的净流入数据变成浮点数
    num_sorted = sorted(num_Pos_cash, key=lambda s: s[1], reverse=True)  # 按照净流入从大到小排序
    sid_stock_cash = [s[0] for s in num_sorted]  # 提取股票代码
    sid_stock_cash = sid_stock_cash[:30]  # 最多选取30支股票
    return sid_stock_cash


def KmeansStrategy3(index_day=3):  # KmeansStrategy2_1的改进版,最后用主力参与度进行排序
    (*_, tradeday_0, tradeday_1, tradeday_2) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                                  order='DESC')[
                                               :index_day]  # 提取中国银行的倒数第三个交易日,作为所有股票的倒数第三个交易日,本行第一个数字为控制变量,默认且最小为3.
    stocks_2 = KmeansData.objects.filter(stock_date__range=(tradeday_2, tradeday_0))  # 获取特定三个交易日的所有股票
    judge_2 = stocks_2.filter(stock_date=tradeday_2).values_list('stock_id', 'price_open',
                                                                 'price_close')  # 获取倒数第三个交易日的股票代码,开盘价,收盘价
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) > float(s[2])]  # 倒数第三日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    judge_1 = stocks_2.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close',
                                                                                              'stock_volumn')  # 倒数第2个交易日的股票代码,开盘价,收盘价
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) > float(s[2])]  # 倒数第2日绿色股票代码
    judge_0 = stocks_2.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close',
                                                                                              'price_low',
                                                                                              'price_high',
                                                                                              'stock_volumn')  # 倒数第一日交易日股票数据
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码

    # 找寻stock_id_list0中下影线特别短,成交量上涨,圆柱实体具有一定长度的股票
    sid_stock = []
    for sid in stock_id_list0:
        prices = [(float(s[1]), float(s[2]), float(s[3]), float(s[4]), int(s[5])) for s in judge_0 if
                  s[0] == sid]  # 获取开盘价, 收盘价,最低价,最高价
        price_open = prices[0][0]
        price_close = prices[0][1]
        price_low = prices[0][2]
        price_high = prices[0][3]
        volumn0 = prices[0][4]
        volumn1 = [int(s[3]) for s in judge_1 if s[0] == sid][0]  # 倒数第二天的成交量
        try:
            if ((price_open - price_low) / price_low < 0.001) and (
                            (price_close - price_open) / (
                                    price_high - price_low) > 0.2) and volumn0 > volumn1:  # 下影线短,开收盘价与最高低价比例的判定
                sid_stock.append(sid)
        except Exception:
            continue

    stocks_cash = CashFlowData.objects.filter(stock_id__in=sid_stock, stock_date=tradeday_0)  # 最新一天的资金净流入数据
    value_cash = stocks_cash.values_list('stock_id', 'maincash_in')  # 提取主力净流入数据
    value_pos_cash = [s for s in value_cash if not s[1].startswith('-')]  # 提取资金流正流入的股票
    value_Pos_cash = [s for s in value_pos_cash if s[1].endswith('万') or s[1].endswith('亿')]  # 去掉资金净流入还不足万元的股票
    num_Pos_cash = [(s[0], float(s[1][:-1])) if s[1].endswith('万') else (s[0], float(s[1][:-1]) * 10 ** 4) for s in
                    value_Pos_cash]  # 将股票的净流入数据变成浮点数
    num_sorted = sorted(num_Pos_cash, key=lambda s: s[1], reverse=True)  # 按照净流入从大到小排序
    sid_stock_cash = [s[0] for s in num_sorted]  # 提取股票代码

    # 按照主力参与程度进行排序
    cstocks = CashFlowData.objects.filter(stock_id__in=sid_stock_cash,
                                          stock_date__range=(tradeday_1, tradeday_0)).order_by('stock_date')
    cdatas0 = cstocks.values_list('stock_id', 'join_degree')
    cdatas1 = defaultdict(list)
    for k, v in cdatas0:
        cdatas1[k].append(float(v[:-1]))

    cdatas2 = [(k, cdatas1[k][1] - cdatas1[k][0]) for k in cdatas1 if
               len(cdatas1[k]) == 2 and cdatas1[k][1] - cdatas1[k][0] > 0]
    cdatas2_sort = sorted(cdatas2, key=lambda s: s[1], reverse=True)
    cdatas3 = cdatas2_sort[:20]  # 呈现的股票数量
    stock_id = [s[0] for s in cdatas3]

    return stock_id


def KmeansStrategy3_1(index_day=3):  # KmeansStrategy3的改进版,最后一日去掉各种繁琐的限制条件 跌/跌/涨
    (*_, tradeday_0, tradeday_1, tradeday_2) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                                  order='DESC')[
                                               :index_day]  # 提取中国银行的倒数第三个交易日,作为所有股票的倒数第三个交易日,本行第一个数字为控制变量,默认且最小为3.
    stocks_2 = KmeansData.objects.filter(stock_date__range=(tradeday_2, tradeday_0))  # 获取特定三个交易日的所有股票
    judge_2 = stocks_2.filter(stock_date=tradeday_2).values_list('stock_id', 'price_open',
                                                                 'price_close')  # 获取倒数第三个交易日的股票代码,开盘价,收盘价
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) > float(s[2])]  # 倒数第三日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    judge_1 = stocks_2.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close')  # 倒数第2个交易日的股票代码,开盘价,收盘价
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) > float(s[2])]  # 倒数第2日绿色股票代码
    judge_0 = stocks_2.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close')  # 倒数第一日交易日股票数据
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码

    # 股票当日涨跌幅小于特定值
    # var_degree = CashFlowData.objects.filter(stock_id__in=stock_id_list0, stock_date=tradeday_0).values_list('stock_id',
    #                                                                                                          'var_degree')
    # var_degree = [s for s in var_degree if s[1].endswith('%')]  # 股票的涨跌幅存在
    # stock_id_list0 = [s[0] for s in var_degree if float(s[1][:-1]) < 3]  # 涨跌幅小于特定数值

    # 最后一日主力资金净流入,并且主力成本与收盘价的差距不能过大(实测后,效果不好)
    # stocks0 = CashFlowData.objects.filter(stock_id__in=stock_id_list0, stock_date=tradeday_0)
    # judge0 = stocks0.values_list('stock_id', 'maincash_in', 'price_close', 'main_cost')
    # s0 = [s for s in judge0 if not s[1].startswith('-')]  # 去掉主力净流出的股票
    # s1 = [s for s in s0 if float(s[2]) - float(s[3]) < 0.1]  # 选出收盘价与主力成本的差值小于0.1的股票
    # stock_id_list0 = [s[0] for s in s1]  # 提取股票代码

    # 按照主力参与程度进行排序
    cstocks = CashFlowData.objects.filter(stock_id__in=stock_id_list0,
                                          stock_date__range=(tradeday_1, tradeday_0)).order_by('stock_date')
    cdatas0 = cstocks.values_list('stock_id', 'join_degree')
    cdatas1 = defaultdict(list)
    for k, v in cdatas0:
        cdatas1[k].append(float(v[:-1]))

    cdatas2 = [(k, cdatas1[k][1] - cdatas1[k][0]) for k in cdatas1 if
               len(cdatas1[k]) == 2 and cdatas1[k][1] - cdatas1[k][0] > 2]  # 主力参与度(今日-昨日)>2%
    cdatas2_sort = sorted(cdatas2, key=lambda s: s[1], reverse=True)
    cdatas3 = cdatas2_sort[:10]  # 呈现的股票数量
    stock_id = [s[0] for s in cdatas3]

    return stock_id


def reverse_kmeans(index_day=4):  # 直接观察跌/跌/涨之后,最后一天大涨的股票规律
    (*_, tradeday_0, tradeday_1, tradeday_2, tradeday_3) = KmeansData.objects.filter(stock_id='601988').dates(
            'stock_date', 'day', order='DESC')[:index_day]  # 本行第一个数字为控制变量,默认且最小为4.
    stocks = KmeansData.objects.filter(stock_date__range=(tradeday_3, tradeday_0))  # 获取特定4个交易日的所有股票
    judge_3 = stocks.filter(stock_date=tradeday_3).values_list('stock_id', 'price_open',
                                                               'price_close')  # 获取倒数第4个交易日的股票代码,开盘价,收盘价
    stock_id_list3 = [s[0] for s in judge_3 if float(s[1]) > float(s[2])]  # 倒数第4日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    judge_2 = stocks.filter(stock_id__in=stock_id_list3, stock_date=tradeday_2).values_list('stock_id', 'price_open',
                                                                                            'price_close')  # 倒数第3个交易日的股票代码,开盘价,收盘价
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) > float(s[2])]  # 倒数第3日绿色股票代码
    judge_1 = stocks.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id', 'price_open',
                                                                                            'price_close')  # 倒数第2日交易日股票数据
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) < float(s[2])]  # 倒数第2日红色股票代码
    judge_0 = stocks.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id', 'price_open',
                                                                                            'price_close')  # 倒数第1日股票数据
    stocks_0 = [s for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票
    stocks_0 = sorted(stocks_0, key=lambda s: float(s[1]) - float(s[2]))
    stocks_choose = stocks_0[:10]
    stock_id_choose = [s[0] for s in stocks_choose]

    return stock_id_choose


# kmeans 的 session3函数,利用自建的数据表KStockList来存取昨日与今日的股票数据,更新状态
def kmeans_session3(request):
    now = datetime.now()  # 获取实时时间
    index_day = 1
    try:
        stock_kid_yes = KStockList.objects.get(pk=1)
    except Exception:
        stock_kid_yes = KStockList.objects.get_or_create(stock_kid_yes=KmeansStrategy2_1(index_day + 3),
                                                         defaults={'pk': 1})
        stock_kid_yes = stock_kid_yes[0]
    stock_kid_yes = stock_kid_yes.stock_kid_yes
    if isinstance(stock_kid_yes, str):
        stock_kid_yes = eval(stock_kid_yes)  # 如此将stock_kid_yes 变成list

    try:
        stock_kid_now = KStockList.objects.get(pk=2)
    except Exception:
        stock_kid_now = KStockList.objects.get_or_create(stock_kid_now=KmeansStrategy2_1(index_day + 2),
                                                         defaults={'pk': 2})  # 实测, pk不能与1重复
        stock_kid_now = stock_kid_now[0]
    stock_kid_now = stock_kid_now.stock_kid_now
    if isinstance(stock_kid_now, str):
        stock_kid_now = eval(stock_kid_now)

    try:
        kflag = KStockList.objects.get(pk=3)
    except Exception:
        kflag = KStockList.objects.get_or_create(kflag=0, defaults={'pk': 3})
        kflag = kflag[0]
    kflag = int(kflag.kflag)

    # 以数据库的方式记录更新状态
    # count_knew = int(request.COOKIES.get('count_knew', False))  # 计算stock_id_new 被调用过几次
    if now.hour >= 16 and not kflag:  # 这里count_new调用一次即可,若鲁棒性太差,可以设置为计数的方式,如count_new<5,当hour<17时,count_new=1
        stock_kid_new = KmeansStrategy2_1(index_day + 2)
        KStockList.objects.filter(pk=3).update(kflag=1)
        if stock_kid_now != stock_kid_new:  # 如果不相等,说明数据有更新
            stock_kid_yes = stock_kid_now
            KStockList.objects.filter(pk=1).update(stock_kid_yes=stock_kid_yes)
            stock_kid_now = stock_kid_new
            KStockList.objects.filter(pk=2).update(stock_kid_now=stock_kid_now)
    if now.hour < 16 and kflag:  # 自己点赞,颇为巧妙
        KStockList.objects.filter(pk=3).update(kflag=0)

    return stock_kid_yes, stock_kid_now


def KmeansStrategy4(index_day=5):  # 寻找股市红三兵 跌/跌/涨/涨/涨,后面三天每天的涨幅低于3%
    (*_, tradeday_0, tradeday_1, tradeday_2, tradeday_3, tradeday_4) = KmeansData.objects.filter(
            stock_id='601988').dates('stock_date', 'day', order='DESC')[
                                                                       :index_day]  # 提取中国银行的倒数第5个交易日,作为所有股票的倒数第5个交易日,本行第一个数字为控制变量,默认且最小为5.
    stocks = KmeansData.objects.filter(stock_date__range=(tradeday_4, tradeday_0))  # 获取特定三个交易日的所有股票
    judge_4 = stocks.filter(stock_date=tradeday_4).values_list('stock_id', 'price_open',
                                                               'price_close')  # 获取倒数第5个交易日的股票代码,开盘价,收盘价
    stock_id_list4 = [s[0] for s in judge_4 if float(s[1]) > float(s[2])]  # 倒数第5日满足开盘价大于收盘价(绿)的股票代码,别忘了将字符串转换为浮点数
    judge_3 = stocks.filter(stock_id__in=stock_id_list4, stock_date=tradeday_3).values_list('stock_id',
                                                                                            'price_open',
                                                                                            'price_close')  # 倒数第4个交易日的股票代码,开盘价,收盘价
    stock_id_list3 = [s[0] for s in judge_3 if float(s[1]) > float(s[2])]  # 倒数第4日绿色股票代码

    judge_2 = stocks.filter(stock_id__in=stock_id_list3, stock_date=tradeday_2).values_list('stock_id',
                                                                                            'price_open',
                                                                                            'price_close')  # 倒数第3日交易日股票数据
    stock_id_list2 = [s[0] for s in judge_2 if float(s[1]) < float(s[2])]  # 倒数第3日红色股票代码
    cstocks = CashFlowData.objects.filter(stock_id__in=stock_id_list2,
                                          stock_date__range=(tradeday_2, tradeday_0))  # 资金流的相关数据
    var_degree2 = cstocks.filter(stock_id__in=stock_id_list2, stock_date=tradeday_2).values_list('stock_id',
                                                                                                 'var_degree')
    datas2 = [s for s in var_degree2 if s[1].endswith('%')]
    stock_id_list2 = [s[0] for s in datas2 if float(s[1][:-1]) < 11]  # 涨幅小于1个百分点

    judge_1 = stocks.filter(stock_id__in=stock_id_list2, stock_date=tradeday_1).values_list('stock_id', 'price_open',
                                                                                            'price_close')  # 倒数第2日交易日股票数据
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) < float(s[2])]  # 倒数第2日红色股票代码
    var_degree1 = cstocks.filter(stock_id__in=stock_id_list1, stock_date=tradeday_1).values_list('stock_id',
                                                                                                 'var_degree')
    datas1 = [s for s in var_degree1 if s[1].endswith('%')]
    stock_id_list1 = [s[0] for s in datas1 if float(s[1][:-1]) < 21]

    judge_0 = stocks.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id', 'price_open',
                                                                                            'price_close')  # 倒数第1日交易日股票数据
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码
    var_degree0 = cstocks.filter(stock_id__in=stock_id_list0, stock_date=tradeday_0).values_list('stock_id',
                                                                                                 'var_degree')
    datas0 = [s for s in var_degree0 if s[1].endswith('%')]
    stock_id_list0 = [s[0] for s in datas0 if float(s[1][:-1]) < 31]

    # 股票当日涨跌幅小于特定值
    # var_degree = CashFlowData.objects.filter(stock_id__in=stock_id_list0, stock_date=tradeday_0).values_list('stock_id',
    #                                                                                                          'var_degree')
    # var_degree = [s for s in var_degree if s[1].endswith('%')]  # 股票的涨跌幅存在
    # stock_id_list0 = [s[0] for s in var_degree if float(s[1][:-1]) < 3]  # 涨跌幅小于特定数值

    # 按照主力参与程度进行排序
    cstocks_join = CashFlowData.objects.filter(stock_id__in=stock_id_list0,
                                               stock_date__range=(tradeday_1, tradeday_0)).order_by('stock_date')
    cdatas0 = cstocks_join.values_list('stock_id', 'join_degree')
    cdatas1 = defaultdict(list)
    for k, v in cdatas0:
        cdatas1[k].append(float(v[:-1]))

    cdatas2 = [(k, cdatas1[k][1] - cdatas1[k][0]) for k in cdatas1 if
               len(cdatas1[k]) == 2 and cdatas1[k][1] - cdatas1[k][0] > 0]
    cdatas2_sort = sorted(cdatas2, key=lambda s: s[1], reverse=True)
    cdatas3 = cdatas2_sort[:10]  # 呈现的股票数量
    stock_id = [s[0] for s in cdatas3]

    # stock_id = stock_id_list0

    return stock_id


# @cache_page(60 * 15)
def k_means(request):
    visitcount(request)
    kdata_dated = KmeansData.objects.filter(stock_date__lte=day_fixed_before_kdata)  # 筛选出过时数据
    kdata_dated.delete()  # 删除

    context_dict = {}  # 上下文字典

    now = datetime.now()  # 获取实时时间

    workday = [0, 1, 2, 3, 4]  # 星期一至星期五
    if (now.weekday() in workday) and (15 <= now.hour < 17):  # 工作日的15:00-16:00之间
        context_dict['time_blank'] = '17点后更新'
        # count_knew = 0
    else:
        index_day = 1  # 最小值为1, 代表最新的一天

        (*_, tradeday_0) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                           :index_day]
        stocks_var = CashFlowData.objects.filter(stock_date=tradeday_0)
        # data_var_degree = stocks_var.values_list('var_degree', flat=True)
        # count_float = (float(x[:-1]) if x.endswith('%') else 0 for x in data_var_degree)
        # count_rise = len([x for x in count_float if x > 0])
        # print('the number of rise stocks:', count_rise)  # 所有print中的数据改成英文
        # print('total stocks:', stocks_var.count())
        # print('the ratio of rise stocks:', count_rise / stocks_var.count())

        stock_id_list = KmeansStrategy3_1(index_day + 2)  # 获取符合选股策略的股票代码, 见上面的函数
        stock_id_list_yes = KmeansStrategy3_1(index_day + 3)
        # stock_id_list = KmeansStrategy4(index_day + 4)
        # stock_id_list_yes = KmeansStrategy4(index_day + 5)
        # stock_id_list_yes = reverse_kmeans(index_day + 3)
        context_dict['trade_day'] = tradeday_0  # 交易日,用在模板的表格中

        # stock_id = kmeans_session3(request)  # session函数
        # stock_id_list = stock_id[1]
        # stock_id_list_yes = stock_id[0]  # 前一天,用来回测数据
        # count_knew = stock_id[2]  # 从session函数返回的count_new,记录stock_kid_now与stock_kid_new是否相等的状态

        stocks_yes = stock_yes_test(stock_id_list_yes, index_day)

        if stocks_yes:
            context_dict['stocks_yes'] = stocks_yes[0]
            context_dict['average_var'] = stocks_yes[1]
            context_dict['average_count'] = stocks_yes[2]
            context_dict['stocks'] = ChangeToEchartsData_kdata(stock_id_list)  # 将选择出的股票转换为符合echarts的数据结构,常规模式

            # context_dict['stocks'] = ChangeToEchartsData()  # 单独调试

    response = render(request, 'choose_stock/k_means.html', context_dict)
    # expire_day = cookie_expire_time(16)  # 每天的16时为cookie的更新时间
    # response.set_cookie('count_knew', count_knew, expires=expire_day)
    # response.set_cookie('count_knew', count_knew, max_age=1)  # 10分钟后cookie到期

    return response


# -----------------------------中线布局相关----------------------------------
def K_middle_Strategy(index_day=2):  # 按照高抛低吸的特点,结合历史数据,寻找K线图的低点.策略:最后两日略涨,最后1日的股价处于历史低点附近
    (*_, tradeday_0, tradeday_1) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                      order='DESC')[
                                   :index_day]  # 提取中国银行交易日日期数据,本行第一个数字为控制变量,默认且最小为2.
    stocks_1 = KmeansData.objects.filter(stock_date__range=(tradeday_1, tradeday_0))  # 获取特定2个交易日的所有股票
    judge_1 = stocks_1.filter(stock_date=tradeday_1).values_list('stock_id', 'price_open',
                                                                 'price_close')  # 获取倒数第2个交易日的股票代码,开盘价,收盘价
    stock_id_list1 = [s[0] for s in judge_1 if float(s[1]) < float(s[2])]  # 倒数第2日红
    judge_0 = stocks_1.filter(stock_id__in=stock_id_list1, stock_date=tradeday_0).values_list('stock_id',
                                                                                              'price_open',
                                                                                              'price_close')  # 倒数第1个交易日的股票代码,开盘价,收盘价
    stock_id_list0 = [s[0] for s in judge_0 if float(s[1]) < float(s[2])]  # 倒数第1日红色股票代码

    # 去掉除权的股票(断崖式下跌的股票),
    stocks_var = CashFlowData.objects.filter(stock_id__in=stock_id_list0, stock_date__lte=tradeday_0).values_list(
            'stock_id', 'var_degree')
    var_list = defaultdict(list)
    for k, v in stocks_var:
        if v.endswith('%'):
            var_list[k].append(float(v[:-1]))
    stock_id_list0 = [k for k in var_list if min(var_list[k]) > -10.5]

    # 股票当日涨跌幅小于特定值
    # var_degree = CashFlowData.objects.filter(stock_id__in=stock_id_list0, stock_date=tradeday_0).values_list('stock_id',
    #                                                                                                          'var_degree')
    # var_degree = [s for s in var_degree if s[1].endswith('%')]  # 股票的涨跌幅存在
    # stock_id_list0 = [s[0] for s in var_degree if float(s[1][:-1]) < 3]  # 涨跌幅小于特定数值

    stocks = KmeansData.objects.filter(stock_id__in=stock_id_list0, stock_date__lte=tradeday_0).order_by('stock_date')
    kdatas0 = stocks.values_list('stock_id', 'price_low', 'price_high')
    kdatas1 = defaultdict(list)
    for k, v1, v2 in kdatas0:
        kdatas1[k].append((float(v1), float(v2)))

    kdatas2 = [(k, min(kdatas1[k])[0], max(kdatas1[k], key=lambda s: s[1])[1]) for k in kdatas1 if
               min(kdatas1[k])[0] > 0]  # 提取每只股票的最低价,最高价,注意提取方法

    kdatas3 = []
    for item in kdatas2:
        stock_id = item[0]
        price_min = item[1]
        price_max = item[2]
        if price_max - price_min > 5:  # 保证最大值与最小值的差不低于特定值,股票有上涨空间
            price_close = [s[2] for s in judge_0 if s[0] == stock_id][0]
            diff1 = float(price_close) - price_min  # 收盘价与最低价的差
            diff2 = price_max - float(price_close)  # 收盘价与最高价的差
            try:
                diff = diff1 / diff2  # 距离差比
            except Exception:
                continue
            kdatas3.append((stock_id, diff))

    kdatas3_sort = sorted(kdatas3, key=lambda s: s[1])  # 距离差比按照从小到大排列
    kdatas4 = kdatas3_sort[:10]
    stock_id = [s[0] for s in kdatas4]

    return stock_id


def k_middle(request):
    visitcount(request)
    context_dict = {}  # 上下文字典

    now = datetime.now()  # 获取实时时间

    workday = [0, 1, 2, 3, 4]  # 星期一至星期五
    if (now.weekday() in workday) and (15 <= now.hour < 16):  # 工作日的15:00-16:00之间
        context_dict['time_blank'] = '16点后更新'
    else:
        index_day = 1  # 最小值为1, 代表最新的一天

        (*_, tradeday_0) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                           :index_day]
        context_dict['trade_day'] = tradeday_0  # 交易日,用在模板的表格中

        stock_id_list = K_middle_Strategy(index_day + 1)  # 获取符合选股策略的股票代码, 见上面的函数
        context_dict['stocks'] = ChangeToEchartsData_kdata(stock_id_list)  # 将选择出的股票转换为符合echarts的数据结构,常规模式

    return render(request, 'choose_stock/k_middle.html', context_dict)


# -----------------------------资金流相关函数---------------------------------
def ChangeToEchartsData_cdata(stock_id_list=['000705', '300016', '002090', '300110']):
    stocks = CashFlowData.objects.filter(stock_id__in=stock_id_list).order_by('stock_date')
    stock_seen = list({(stock.stock_id, stock.stock_name) for stock in stocks})
    # stock_seen = Name_Id.objects.filter(stock_id__in=stock_id_list).values_list('stock_id', 'stock_name')
    stocks_new = []
    for sid in stock_seen:
        stock = {}  # 重构每支股票
        stock['stock_id'] = sid[0]
        stock['stock_name'] = sid[1]
        stock['stock_date'] = [str(s.stock_date) for s in stocks if s.stock_id == sid[0]]
        maincash_data = [s.maincash_in for s in stocks if s.stock_id == sid[0]]
        maincash_data_rise = []  # 资金净流入
        maincash_data_fall = []  # 资金净流出
        for eachdata in maincash_data:
            if not (eachdata.endswith('万') or eachdata.endswith('亿')):
                number = 0  # 如'-'或者小于1万的数据,全部近似处理为0
            elif eachdata.endswith('亿'):
                number = float(eachdata[:-1]) * 10 ** 4
            else:
                number = float(eachdata[:-1])
            # try:
            #     unit = eachdata[-1]  # 资金流数据单位,"亿"或者"万"
            #     number = float(eachdata[:-1])  # 数字,字符串形式
            # except Exception as e:
            #     print('switch number error:', e, sid)
            #     number = 0
            # if unit == '亿':
            #     number *= 10 ** 4
            if number > 0:
                maincash_data_rise.append(number)
                maincash_data_fall.append('-')
            else:
                maincash_data_rise.append('-')
                maincash_data_fall.append(number)
        stock['maincash_data_rise'] = maincash_data_rise
        rise_temp = [x for x in maincash_data_rise if isinstance(x, float)]
        stock['maincash_data_fall'] = maincash_data_fall
        fall_temp = [x for x in maincash_data_fall if isinstance(x, float)]
        try:
            stock['average_rise'] = sum(rise_temp) / len(rise_temp)  # 净流入平均值
            stock['average_fall'] = sum(fall_temp) / len(fall_temp)  # 净流出平均值
            # 主力净占比
            # maincash_rate = [float(s.maincash_in_rate[:-1]) for s in stocks if s.stock_id == sid[0]]  # 单位为%, 比实际数大100倍
        except Exception as e:
            print('switch number or division error:', e, sid)
            # continue
        # maincash_rate = [float(s.maincash_in_rate[:-1]) for s in stocks if s.stock_id == sid[0]]  # 单位为%, 比实际数大100倍
        maincash_rate = [s.maincash_in_rate for s in stocks if s.stock_id == sid[0]]
        maincash_rate = [float(s[:-1]) if s != '-' else 0 for s in
                         maincash_rate]  # 貌似此处当s=='-'是,s必须设为0,echarts的'line'图需要
        stock['maincash_rate'] = maincash_rate

        # 收盘价与主力成本
        stock['price_close'] = [float(s.price_close) for s in stocks if s.stock_id == sid[0]]
        main_cost = [s.main_cost for s in stocks if s.stock_id == sid[0]]
        stock['main_cost'] = [float(s) if s else '-' for s in main_cost]  # 列表解析,带else的,要写前面

        #  机构参与度和控盘类型
        join_degree = (s.join_degree for s in stocks if s.stock_id == sid[0])
        stock['join_degree'] = [float(s[:-1]) if s else '-' for s in join_degree]  # 空白时替换为'-'号,不然echarts这贱人会犯莫名其妙的错误
        control_type = [s.control_type for s in stocks if s.stock_id == sid[0]]
        stock['control_type'] = [s if s else '-' for s in control_type]

        stocks_new.append(stock)
    return stocks_new


def CashFlowStrategy1(index_day=1):  # 策略1: 最后一天净流入,大于平均值,(收盘价-成本价)从小到大排列10个
    (*_, tradeday_0) = CashFlowData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                       :index_day]  # 获取最近的交易日,"[]"中的数最小为1
    stocks = CashFlowData.objects.filter(stock_date__lte=tradeday_0).order_by('stock_date')
    id_maincash = stocks.values_list('stock_id', 'maincash_in')
    id_maincash2 = defaultdict(list)  # 初始化字典
    for k, v in id_maincash:
        id_maincash2[k].append(v)

    stock_id1 = []  # 储存最后一天主力资金净流入大于净流入平均值的股票代码
    for k in id_maincash2:
        k_maincash = id_maincash2[k]
        pos_maincash = [x for x in k_maincash if not x.startswith('-')]  # 去掉以'-'开头的maincash
        try:
            float_maincash = [float(x[:-1]) if x[-1] == '万' else float(x[:-1]) * 10 ** 4 for x in
                              pos_maincash]  # 转换为浮点数
            average_maincash = sum(float_maincash) / len(float_maincash)
            if k_maincash[-1][-1] == '万':
                last_maincash = float(k_maincash[-1][:-1])
            else:
                last_maincash = float(k_maincash[-1][:-1]) * 10 ** 4
            if last_maincash > average_maincash * 2:  # 净流入大于1.5倍的平均值
                stock_id1.append(k)
        except Exception as e:
            print('switch number error:', e, k)
            continue

    stocks1 = stocks.filter(stock_id__in=stock_id1, stock_date=tradeday_0)
    judge1 = stocks1.values_list('stock_id', 'price_close', 'main_cost')
    sorted_judge = sorted(judge1, key=lambda s: float(s[1]) - float(s[2]))  # 以(收盘价-开盘价)又小到大排序
    stocks_id2 = sorted_judge[:20]  # 前特定数量的股票,不足也行
    stocks_id2_1 = [s[0] for s in stocks_id2]  # 取出股票代码
    return stocks_id2_1


def CashFlowStrategy2(index_day=1):  # 策略2: 最后一天净流入,大于平均值,前三次净流入均小于平均值,(收盘价-成本价)从小到大排列10个
    (*_, tradeday_0) = CashFlowData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                       :index_day]  # 获取最近的交易日,"[]"中的数最小为1
    stocks = CashFlowData.objects.filter(stock_date__lte=tradeday_0).order_by('stock_date')
    # test_id = ['002647', '603519', '600228', '002587', '002762', '002569', '300284', '002379']
    # stocks = CashFlowData.objects.filter(stock_id__in=test_id, stock_date__lte=tradeday_0).order_by('stock_date')
    id_maincash = stocks.values_list('stock_id', 'maincash_in')
    id_maincash2 = defaultdict(list)  # 初始化字典
    for k, v in id_maincash:
        id_maincash2[k].append(v)

    stock_id1 = []  # 储存最后一天主力资金净流入大于净流入平均值的股票代码
    for k in id_maincash2:

        #  下面三行代码放在此处严重影响性能, 尽量不要在循环中去不停地访问数据库
        # k_other_data = stocks.filter(stock_id=k).values_list('price_close', 'main_cost')  # 取得股票的收盘价与主力成本价
        # if not (k_other_data.last()[0] and k_other_data.last()[1]):  # 如果最后一天的收盘价或者主力成本不存在,则过滤掉该函数
        #     continue
        k_maincash = id_maincash2[k]
        pos_maincash = [x for x in k_maincash if not x.startswith('-')]  # 去掉以'-'开头的maincash
        if not pos_maincash:  # 去掉查询的最后一天无主力资金净流入数据的空股票,需不需要加pos_maincash[-1]
            continue
        elif not pos_maincash[-1]:
            continue
        if not (pos_maincash[-1].endswith('万') or pos_maincash[-1].endswith('亿')):  # 去掉万以下的数据
            continue

        try:
            float_maincash = [float(x[:-1]) if x[-1] == '万' else float(x[:-1]) * 10 ** 4 for x in
                              pos_maincash]  # 转换为浮点数
            average_maincash = sum(float_maincash) / len(float_maincash)

            if float_maincash[-2] < average_maincash and float_maincash[-3] < average_maincash and float_maincash[
                -4] < average_maincash:
                ave3_less = True
            else:
                ave3_less = False
                continue

            if k_maincash[-1][-1] == '万':
                last_maincash = float(k_maincash[-1][:-1])
            else:
                last_maincash = float(k_maincash[-1][:-1]) * 10 ** 4

            if last_maincash > average_maincash * 2 and ave3_less and last_maincash > 1000:  # 净流入大于特定倍数的平均值, 大于1000(判定为热门股票)
                k_other_data = stocks.filter(stock_id=k).values_list('price_close', 'main_cost',
                                                                     'var_degree')  # 取得股票的收盘价与主力成本价
                if not (k_other_data.last()[0] and k_other_data.last()[1] and k_other_data.last()[
                    2] != '-'):  # 如果最后一天的收盘价或者主力成本不存在,或者涨跌幅为'-',则过滤掉该函数
                    continue
                else:
                    stock_id1.append(k)
        except Exception as e:
            print('switch number error:', e, k)
            continue

    stocks1 = stocks.filter(stock_id__in=stock_id1, stock_date=tradeday_0)
    judge1 = stocks1.values_list('stock_id', 'price_close', 'main_cost', 'var_degree')
    judge2 = [s for s in judge1 if
              float(s[1]) - float(s[2]) <= 0.1 and float(s[3][:-1]) < 9.8]  # 收盘价-主力成本<=0.1 并且当天涨幅<9.8%
    sorted_judge = sorted(judge2, key=lambda s: float(s[1]) - float(s[2]))  # 以(收盘价-开盘价)由小到大排序
    stocks_id2 = sorted_judge[:20]  # 前特定数量的股票,不足也行
    stocks_id2_1 = [s[0] for s in stocks_id2]  # 取出股票代码
    return stocks_id2_1


def stock_yes_test(stock_list_yes, index_day):
    (*_, tradeday_0) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                       :index_day]
    stocks_all_yes = CashFlowData.objects.filter(stock_date=tradeday_0)  # 采用了CashFlowDat的数据库,所以最好每日17点后更新
    data_var_degree = stocks_all_yes.values_list('var_degree', flat=True)
    sorted_var_degree = sorted((float(x[:-1]) if x.endswith('%') else 0 for x in data_var_degree),
                               reverse=True)  # 将涨跌幅按照从小到大排序
    data_yes = stocks_all_yes.filter(stock_id__in=stock_list_yes).values('stock_id', 'stock_name',
                                                                         'var_degree')  # 特定股票数据
    stocks_yes = []  # 记录前一日的股票
    for eachdata in data_yes:
        each_var_degree = eachdata['var_degree']
        eachdata['var_degree'] = each_var_degree if each_var_degree.endswith('%') else '0%'
        vd = float(each_var_degree[:-1]) if each_var_degree.endswith('%') else 0  # 去掉百分号后的单支股票涨跌幅
        eachdata['vd'] = vd
        each_count = len([x for x in sorted_var_degree if x > vd]) + 1  # 每支股票的涨跌排名
        eachdata['var_count'] = each_count  # 加入单支股票的字典中
        stocks_yes.append(eachdata)

    if stocks_yes:
        stocks_yes = sorted(stocks_yes, key=lambda x: x['vd'], reverse=True)  # 将股票按照涨跌幅重新排序

        average_var = sum(x['vd'] for x in stocks_yes) / len(stocks_yes)  # 股票的平均涨跌幅
        average_count = len([x for x in sorted_var_degree if x > average_var]) + 1  # 平均涨跌幅对应的涨跌排名
        average_var = '{:0.2f}'.format(average_var) + '%'

        return stocks_yes, average_var, average_count


# capital 的 session3 函数
def capital_session3(request):
    now = datetime.now()  # 获取实时时间
    index_day = 1
    try:
        stock_cid_yes = CStockList.objects.get(pk=1)  # 运行速度快
    except Exception:
        stock_cid_yes = CStockList.objects.get_or_create(stock_cid_yes=CashFlowStrategy2(index_day + 1),
                                                         defaults={'pk': 1})  # 运行速度慢,每次都要计算CashFlowStrategy2函数
        stock_cid_yes = stock_cid_yes[0]
    stock_cid_yes = stock_cid_yes.stock_cid_yes
    if isinstance(stock_cid_yes, str):
        stock_cid_yes = eval(stock_cid_yes)  # 如此将stock_cid_yes 变成list

    try:
        stock_cid_now = CStockList.objects.get(pk=2)
    except Exception:
        stock_cid_now = CStockList.objects.get_or_create(stock_cid_now=CashFlowStrategy2(index_day), defaults={'pk': 2})
        stock_cid_now = stock_cid_now[0]
    stock_cid_now = stock_cid_now.stock_cid_now
    if isinstance(stock_cid_now, str):
        stock_cid_now = eval(stock_cid_now)

    try:
        cflag = CStockList.objects.get(pk=3)
    except Exception:
        cflag = CStockList.objects.get_or_create(cflag=0, defaults={'pk': 3})
        cflag = cflag[0]
    cflag = int(cflag.cflag)

    if now.hour >= 17 and not cflag:
        stock_cid_new = CashFlowStrategy2(index_day)
        CStockList.objects.filter(pk=3).update(cflag=1)
        if stock_cid_now != stock_cid_new:  # 如果不相等,说明数据有更新
            stock_cid_yes = stock_cid_now
            CStockList.objects.filter(pk=1).update(stock_cid_yes=stock_cid_yes)
            stock_cid_now = stock_cid_new
            CStockList.objects.filter(pk=2).update(stock_cid_now=stock_cid_now)
    if now.hour < 17 and cflag:  # 其余时间删除count_new的session
        CStockList.objects.filter(pk=3).update(cflag=0)

    return stock_cid_yes, stock_cid_now


def c_control_strategy(index_day):  # 根据主力控盘,结合资金流的选股策略
    (*_, tradeday_0, tradeday_1) = CashFlowData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                        order='DESC')[
                                   :index_day]  # 获取最近的交易日,"[]"中的数最小为2
    stocks = CashFlowData.objects.filter(stock_date__range=(tradeday_1, tradeday_0)).order_by('stock_date')
    stocks_yes = stocks.filter(Q(control_type='不控盘') | Q(control_type='轻度控盘'), stock_date=tradeday_1)  # 注意此处使用了Q对象查询方法
    stock_id_yes = stocks_yes.values_list('stock_id', flat=True)  # 获取昨日的股票代码

    # 去掉当天主力成本价远低于收盘价的股票
    # stocks_t1 = stocks.filter(stock_date=tradeday_0, stock_id__in=stock_id_yes).values_list('stock_id', 'price_close',
    #                                                                                         'main_cost')
    # stock_id_yes = [s[0] for s in stocks_t1 if float(s[1]) - float(s[2]) <= 0.5]  # 收盘价-成本价小于: 0.1

    # 去掉当天主力净流入超过一定数额的股票
    stocks_t1 = stocks.filter(stock_date=tradeday_0, stock_id__in=stock_id_yes).values_list('stock_id', 'maincash_in')
    stock_id_yes = [s[0] for s in stocks_t1 if not s[1].startswith('-')]  # 取消主力净流出的股票

    stocks0 = stocks.filter(stock_id__in=stock_id_yes)
    datas0 = stocks0.values_list('stock_id', 'join_degree')
    datas1 = defaultdict(list)
    for k, v in datas0:
        datas1[k].append(float(v[:-1]))

    datas2 = [(k, datas1[k][1] - datas1[k][0]) for k in datas1 if len(datas1[k]) == 2]
    datas2_sort = sorted(datas2, key=lambda s: s[1], reverse=True)
    datas3 = datas2_sort[:10]  # 呈现的股票数量
    stock_id = [s[0] for s in datas3]

    print(stock_id)

    return stock_id


def c_control_strategy2(index_day):  # 根据主力控盘,结合资金流的选股策略,当日主力净占比小于特定值
    (*_, tradeday_0, tradeday_1) = CashFlowData.objects.filter(stock_id='601988').dates('stock_date', 'day',
                                                                                        order='DESC')[
                                   :index_day]  # 获取最近的交易日,"[]"中的数最小为2
    stocks = CashFlowData.objects.filter(stock_date__range=(tradeday_1, tradeday_0)).order_by('stock_date')
    stocks_yes = stocks.filter(stock_date=tradeday_1).values_list('stock_id', 'maincash_in_rate')
    stocks_yes = [s for s in stocks_yes if s[1].endswith('%')]
    stock_id_yes = [s[0] for s in stocks_yes if float(s[1][:-1]) < -20]  # 昨日主力净占比小于特定数值的股票代码

    # 去掉当天主力成本价远低于收盘价的股票
    # stocks_t1 = stocks.filter(stock_date=tradeday_0, stock_id__in=stock_id_yes).values_list('stock_id', 'price_close',
    #                                                                                         'main_cost')
    # stock_id_yes = [s[0] for s in stocks_t1 if float(s[1]) - float(s[2]) <= 0.5]  # 收盘价-成本价小于: 0.1

    # 选取当天主力净占比小于一定数额的股票
    stocks_t1 = stocks.filter(stock_date=tradeday_0, stock_id__in=stock_id_yes).values_list('stock_id',
                                                                                            'maincash_in_rate')
    stocks_t1 = [s for s in stocks_t1 if s[1].endswith('%')]
    stock_id_yes = [s[0] for s in stocks_t1 if 0 < float(s[1][:-1]) < 5]  # 当日主力净流入绝对值小于特定数值的股票

    stocks0 = stocks.filter(stock_id__in=stock_id_yes)
    datas0 = stocks0.values_list('stock_id', 'join_degree')
    datas1 = defaultdict(list)
    for k, v in datas0:
        datas1[k].append(float(v[:-1]))

    datas2 = [(k, datas1[k][1] - datas1[k][0]) for k in datas1 if len(datas1[k]) == 2]
    datas2_sort = sorted(datas2, key=lambda s: s[1], reverse=True)
    datas3 = datas2_sort[:10]  # 呈现的股票数量
    stock_id = [s[0] for s in datas3]

    print(stock_id)

    return stock_id


def c_middle_strategy(index_day=1):  # 资金流中线选股策略,净流入资金占比最少,最后一天净流入
    (*_, tradeday_0) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                       :index_day]  # 提取中国银行交易日日期数据,本行第一个数字为控制变量,默认且最小为1.
    stocks_0 = CashFlowData.objects.filter(stock_date=tradeday_0)
    judge_0 = stocks_0.values_list('stock_id', 'maincash_in')
    stock_id_list0 = [s[0] for s in judge_0 if not s[1].startswith('-')]  # 去掉净流出的股票代码

    stocks = CashFlowData.objects.filter(stock_id__in=stock_id_list0, stock_date__lte=tradeday_0)
    datas0 = stocks.values_list('stock_id', 'maincash_in')
    datas1 = defaultdict(list)
    for k, v in datas0:
        if v != '-':  # 去掉当天无净流入的数据
            datas1[k].append(v)

    datas2 = []  # 储存股票代码与占比数据
    for k in datas1:
        pos_maincash = []  # 储存净流入的股票数据
        neg_maincash = []  # 储存净流出的股票数据
        maincash_in = datas1[k]
        if len(maincash_in) < 64 - index_day:  # 去掉各种新股,不连续的股票
            continue
        for each_cash in maincash_in:
            if each_cash.endswith('万'):
                num_cash = float(each_cash[:-1])
            elif each_cash.endswith('亿'):
                num_cash = float(each_cash[:-1]) * 10 ** 4
            else:  # 小于万的净流入/出数据
                num_cash = float(each_cash[:-1]) / 10 ** 4
            if num_cash > 0:
                pos_maincash.append(num_cash)
            else:
                neg_maincash.append(num_cash)
        try:
            diff = sum(pos_maincash) / abs(sum(neg_maincash))  # 净流入占净流出的比例
        except Exception:
            print('division by zero:', k)
            continue
        datas2.append((k, diff))

    datas2_sort = sorted(datas2, key=lambda s: s[1])
    datas3 = datas2_sort[:10]
    stock_id = [s[0] for s in datas3]

    return stock_id


# @cache_page(60 * 15)  # 有了session后,貌似不用缓存也很快了,最终不用session也快了.
def capital(request):
    visitcount(request)
    # 删除过期数据...
    cdata_dated = CashFlowData.objects.filter(stock_date__lte=day_fixed_before_cdata)  # 筛选出过时数据
    cdata_dated.delete()  # 删除

    context_dict = {}

    now = datetime.now()  # 获取实时时间

    workday = [0, 1, 2, 3, 4]
    if (now.weekday() in workday) and (15 <= now.hour < 17):  # 工作日的15:00-17:00之间
        context_dict['time_blank'] = '17点后更新'
        # count_cnew = 0
    else:
        # stock_id_list = ['603016']  # 测试用

        index_day = 1  # 最小为1(当前), 2(前一天)
        (*_, tradeday_0) = KmeansData.objects.filter(stock_id='601988').dates('stock_date', 'day', order='DESC')[
                           :index_day]

        stock_id_list = c_control_strategy2(index_day + 1)
        stock_id_list_yes = c_control_strategy2(index_day + 2)
        # stock_id_list = c_middle_strategy(index_day + 0)
        # stock_id_list_yes = c_middle_strategy(index_day + 1)
        context_dict['trade_day'] = tradeday_0

        # stock_id = capital_session3(request)  # session函数
        # stock_id_list = stock_id[1]
        # stock_id_list_yes = stock_id[0]  # 前一天,用来回测数据
        # count_cnew = stock_id[2]  # 从session函数返回的count_new,记录stock_id_now与stock_id_new是否相等的状态

        stocks_yes = stock_yes_test(stock_id_list_yes, index_day)  # 前一天选择的股票进行测试

        if stocks_yes:
            context_dict['stocks_yes'] = stocks_yes[0]
            context_dict['average_var'] = stocks_yes[1]
            context_dict['average_count'] = stocks_yes[2]
        context_dict['stocks'] = ChangeToEchartsData_cdata(stock_id_list)

    response = render(request, 'choose_stock/capital.html', context_dict)
    # expire_day = cookie_expire_time(17)  # 每天的16时为cookie的更新时间
    # response.set_cookie('count_cnew', count_cnew, expires=expire_day)
    # response.set_cookie('count_cnew', count_cnew, max_age=60 * 10)  # 设置cookie过期时间为10分钟

    return response


# ---------------------------个股讯息--------------------------------------
def search(request):
    visitcount(request)
    context = {}
    if request.method == 'POST':
        id_name = request.POST['id_name']  # 对应模板中input的name值
        stock_id_name = Name_Id.objects.all().values_list('stock_id', 'stock_name')  # 取得所有的股票代码及名称
        special_stock = [s for s in stock_id_name if id_name in s]
        if special_stock:
            return redirect('choose_stock.views.stock_detail', stock_id=special_stock[0][0])  # 必须加上return
        else:
            context['info'] = '无此股票讯息,请重新输入'
    return render(request, 'choose_stock/search.html', context)


def stock_detail(request, stock_id):
    visitcount(request)
    context = {}
    stock_id1 = [stock_id]
    try:
        context['stock_c'] = ChangeToEchartsData_cdata(stock_id1)[0]
        context['stock_k'] = ChangeToEchartsData_kdata(stock_id1)[0]
        stock_name = Name_Id.objects.filter(stock_id=stock_id).values_list('stock_name', flat=True)[0]
        context['news'] = News.objects.filter(content__contains=stock_name).order_by('-published_time')
    except Exception as e:
        print('read stock information error:', e, stock_id)
    return render(request, 'choose_stock/stock_detail.html', context)


# -----------------------------访客统计--------------------------------
def visitcount(request):
    ip_address = request.META['REMOTE_ADDR']
    visit_time = datetime.now()
    visit_page = request.path
    visit_device = request.META['HTTP_USER_AGENT']
    VisitData.objects.create(ip_address=ip_address, visit_time=visit_time, visit_page=visit_page,
                             visit_device=visit_device)  # 保存数据


def visitdata(request):
    visits_dated = VisitData.objects.filter(visit_time__lte=day_fixed_before_visit)  # 筛选出过时数据
    visits_dated.delete()  # 删除

    context_dict = {}
    visits_today = VisitData.objects.filter(visit_time__day=now.day).order_by('-visit_time')  # 昨日访客
    visits_yes = VisitData.objects.filter(visit_time__day=yesterday.day).order_by('-visit_time')  # 今日访客
    context_dict['visits_today'] = visits_today
    context_dict['visits_yes'] = visits_yes
    return render(request, 'choose_stock/visitdata.html', context_dict)

# 待办事项:
# 1.优化k线图的选股策略:当日主力资金净流入大于0,主力净流入从高到低排序,观察历史数据------基本成功------
# 2.添加session,保存上一日选择的股票------基本成功------
# 3.修改删除到期股票的方法,尝试用总数控制的方式--不成功
# 4.优化资金流选股策略:结合主力是否控盘,观察历史数据
# 5.改变网络的前端布局,目前太丑了
# 6.每个新闻页增加相关历史消息
# 7.结合情感分析,优化利好/利空消息的选择
# 8.网站访问统计
# 9.K线图停盘数据优化------成功------
# 10.股票的超链接优化------成功------
# 11.回测表格的手机端优化
# 12.搜索页优化,不要单独放一个页面
# 13.股票昨日与今日数据储存优化------成功------
# 14.探索当日资金净流入的绝对值小于某个小的数(如1500万),但主力参与度较高的股票
# 15.探索当日股价下跌,但资金净流入的股票;或连续股价下跌,但资金连续净流入的股票.
# 16.东方财富网资金流界面数据更新经常不及时,考虑换用腾讯股票接口获取资金流数据.
