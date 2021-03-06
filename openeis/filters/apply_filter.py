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

import datetime
from openeis.projects import models
from openeis.filters import column_modifiers
from pytz import timezone

def apply_filter_config(dataset_id,config):

    sensoringest = models.SensorIngest.objects.get(pk=dataset_id)
    datamap = sensoringest.map

    tz_str = models._finditem(datamap.map,'timezone')

    sensors = list(datamap.sensors.all())
    sensor_names = [s.name for s in sensors]
    sensordata = [sensor.data.filter(ingest=sensoringest) for sensor in sensors]
    generators = {}
    for name, qs in zip(sensor_names, sensordata):
        #TODO: Add data type from schema
        value = {"gen":_iter_data(qs, tz_str),
                 "type":None}
        generators[name] = value

    generators, errors = _create_and_update_filters(generators, config)

    if errors:
        return errors

    datamap.id = None
    datamap.name = datamap.name+' version - '+str(datetime.datetime.now())
    datamap.save()

    sensoringest.name = str(sensoringest.id) + ' - '+str(datetime.datetime.now())
    sensoringest.id = None
    sensoringest.map = datamap
    sensoringest.save()



    for sensor in sensors:
        sensor.id= None
        sensor.map = datamap
        sensor.save()
        data_class = sensor.data_class
        generator = generators[sensor.name]['gen']
        sensor_data_list = []
        for time,value in generator:
            sensor_data = data_class(sensor=sensor, ingest=sensoringest,
                                     time=time, value=value)
            sensor_data_list.append(sensor_data)
            if len(sensor_data_list) >= 1000:
                data_class.objects.bulk_create(sensor_data_list)
                sensor_data_list = []
        if sensor_data_list:
            data_class.objects.bulk_create(sensor_data_list)

    return datamap.id

def _iter_data(sensordata, tz_str):
    if tz_str is None:
        tz = timezone('UTC')
    else:
        tz = timezone(tz_str)

    for data in sensordata:
        if data.value is not None:
            yield data.time.astimezone(tz), data.value

def _create_and_update_filters(generators, configs):
    errors = []

    print("column mods: ", column_modifiers)

    for topic, filter_name, filter_config in configs:
        if not isinstance(topic, str):
            topic = topic[0]
        parent_filter_dict = generators.get(topic)
        if parent_filter_dict is None:
            errors.append('Invalid Topic for DataMap: ' + str(topic))
            continue

        parent_filter = parent_filter_dict['gen']
        parent_type = parent_filter_dict['type']

        filter_class = column_modifiers.get(filter_name)
        if filter_class is None:
            errors.append('Invalid filter name: ' + str(filter_name))
            continue

        try:
            new_filter = filter_class(parent=parent_filter, **filter_config)
        except Exception as e:
            errors.append('Error configuring filter: '+str(e))
            continue

        value = parent_filter_dict.copy()

        value['gen']=new_filter
        value['type']=parent_type

        generators[topic] = value

    return generators, errors
