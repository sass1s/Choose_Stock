# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-25 14:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('choose_stock', '0003_auto_20160613_2103'),
    ]

    operations = [
        migrations.CreateModel(
            name='Name_Id',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_name', models.CharField(max_length=16, unique=True)),
                ('stock_id', models.CharField(max_length=8, unique=True)),
            ],
        ),
    ]
