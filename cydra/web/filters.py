# -*- coding: utf-8 -*-
#
# Copyright 2012 Manuel Stocker <mensi@mensi.ch>
#
# This file is part of Cydra.
#
# Cydra is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cydra is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cydra.  If not, see http://www.gnu.org/licenses

from flask import url_for

filters = [any]

def filter(f):
    filters.append(f)
    return f

@filter
def sort_user_keyed_dict(value):
    return sorted(value.items(), key=lambda x: x[0].full_name if not x[0].is_guest else "")

@filter
def sort_attribute(value, attribute):
    return sorted(value, key=lambda x: getattr(x, attribute))

@filter
def escape_js(value):
    res = str(value)
    res = res.replace("'", r"\'")
    res = res.replace("\n", r"\n")
    return res

@filter
def urlize(value, **kwargs):
    if '://' in value or value.startswith('/'):
        return value
    else:
        return url_for(value, **kwargs)
