# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright (c) 2014, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.
#
#
# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization
# that has cooperated in the development of these materials, makes
# any warranty, express or implied, or assumes any legal liability
# or responsibility for the accuracy, completeness, or usefulness or
# any information, apparatus, product, software, or process disclosed,
# or represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does
# not necessarily constitute or imply its endorsement, recommendation,
# or favoring by the United States Government or any agency thereof,
# or Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830
#
#}}}



import abc
import logging
import pkgutil, importlib

from openeis.core.descriptors import (ConfigDescriptorBaseClass,
                                      SelfDescriptorBaseClass)

class BaseFilter(SelfDescriptorBaseClass,
                 ConfigDescriptorBaseClass,
                 metaclass=abc.ABCMeta):
    def __init__(self, parent=None):
        self.parent = parent

    @abc.abstractmethod
    def __iter__(self):
        pass

    @classmethod
    @abc.abstractmethod
    def filter_type(cls):
        pass

class SimpleRuleFilter(BaseFilter, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def rule(self, time, value):
        """Must return time, value pair."""

    def __iter__(self):
        def generator():
            for dt, value in self.parent:
                yield self.rule(dt, value)
        return generator()

    @classmethod
    def filter_type(cls):
        return "other"

column_modifiers = {}

def register_column_modifier(klass):
    column_modifiers[klass.__name__] = klass
    return klass

_extList = [name for _, name, _ in pkgutil.iter_modules(__path__)]

extDict = {}

for extName in _extList:
    print('Importing module: ', extName)
    try:
        module = __import__(extName,globals(),locals(),[], 1)
    except Exception as e:
        logging.error('Module {name} cannot be imported. Reason: {ex}'.format(name=extName, ex=e))
        continue

    extDict[extName] = module