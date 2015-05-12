# -*- coding: utf-8 -*- 
# #####################################################################
# 
# OpenERP, Open Source Management Solution 
# Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>). 
# Copyright (C) 2013 INIT Tech Co., Ltd (http://init.vn). 
# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU Affero General Public License for more details. 
# 
# You should have received a copy of the GNU Affero General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>. 
# 
######################################################################

import calendar
import datetime
from dateutil.relativedelta import relativedelta


def days_of_month(date):
    """
    Return number of days of month which contains date.
    Eg: number of days of month which contains 01/01/2013 is: 31 days
    """
    date = str_to_date(date)
    return calendar.monthrange(date.year, date.month)[1]


def date_after_n_days(date, n):
    """
    Return date after n days
    Eg: date = 01/01/2013, n = 10 => 11/01/2013
    """
    return str_to_date(date) + relativedelta(days=+n)


def days_of_year(year):
    """
    Number of days in year
    Eg: number of days in year 2013 is: 365
    """
    return calendar.isleap(year) and 366 or 365


def last_day_of_month(date):
    """
    Get the last day of month
    Eg: the last day of month which contains 01/01/2013 is: 31
    """
    return days_of_month(str_to_date(date))


def first_date_of_month(date):
    """
    Get the first date of month
    Eg: the first date of month which contains 15/01/2013 is: 01/01/2013
    """
    return str_to_date(date) + relativedelta(day=1)


def last_date_of_month(date):
    """
    Return the last date of month.
    Eg: last date of month which contains 15/01/2013 is: 31/01/2013
    """
    return str_to_date(date) + relativedelta(day=1, months=+1, days=-1)


def first_date_of_next_month(date, month=1):
    """
    Return the first date of next month(s)
    Eg: First date of month which contains date: 15/01/2013 is: 01/02/2013
    """
    return str_to_date(date) + relativedelta(day=1, months=+month)


def date_after_next_month(date, month=1):
    """
    Return date after next month
    Eg: date after 2 month from 15/01/2013 is: 15/03/2013
    """
    return str_to_date(date) + relativedelta(months=+1)


def last_date_of_next_month(date, month=1):
    """
    Return last date of next month which contains date
    Eg: last date of next month which contains 15/01/2013 is: 28/02/2013
    """
    return date + relativedelta(day=1, months=+month, days=-1)


def date_after_previous_month(date):
    """
    Return date after previous month
    Eg: date after 2 month from 15/03/2013 is: 15/02/2013
    """
    return str_to_date(date) + relativedelta(months=-1)


def total_days(date, number_of_month):
    """
    Return number of days between date and n month(s) after it
    Eg: date = 15/01/2013 and number of months are 2; is: 59 days
    """
    date = str_to_date(date)
    new_date = date + relativedelta(months=+number_of_month)
    return (new_date - date).days


def is_first_day_of_month(date):
    """
    Check this date whether is first date of month or not
    """
    return (str_to_date(date).day == 1) and True or False


def is_last_day_of_month(date):
    """
    Check this date whether is last date of month or not
    """
    return (str_to_date(date).day == last_day_of_month(date)) and True or False


def number_days_between_date(date1, date2):
    """
    Return number of days between 2 date
    """
    return (str_to_date(date1) - str_to_date(date2)).days


def str_to_date(date):
    """
    Convert string to date type
    """
    if type(date) == type(''):
        return datetime.datetime.strptime(date, '%Y-%m-%d').date()
    return date
    
