'''
Copyright (c) 2014, Battelle Memorial Institute
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of the FreeBSD Project.
'''
'''
This material was prepared as an account of work sponsored by an
agency of the United States Government.  Neither the United States
Government nor the United States Department of Energy, nor Battelle,
nor any of their employees, nor any jurisdiction or organization
that has cooperated in the development of these materials, makes
any warranty, express or implied, or assumes any legal liability
or responsibility for the accuracy, completeness, or usefulness or
any information, apparatus, product, software, or process disclosed,
or represents that its use would not infringe privately owned rights.

Reference herein to any specific commercial product, process, or
service by trade name, trademark, manufacturer, or otherwise does
not necessarily constitute or imply its endorsement, recommendation,
r favoring by the United States Government or any agency thereof,
or Battelle Memorial Institute. The views and opinions of authors
expressed herein do not necessarily state or reflect those of the
United States Government or any agency thereof.

PACIFIC NORTHWEST NATIONAL LABORATORY
operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
under Contract DE-AC05-76RL01830
'''
import datetime
import logging
from openeis.applications import (DrivenApplicationBaseClass,
                                  OutputDescriptor,
                                  ConfigDescriptor,
                                  InputDescriptor,
                                  Results,
                                  ApplicationDescriptor)

econ1 = 'Temperature Sensor Dx'
econ2 = 'Economizer Correctly ON Dx'
econ3 = 'Economizer Correctly OFF Dx'
econ4 = 'Excess Outdoor-air Intake Dx'
econ5 = 'Insufficient Outdoor-air Intake Dx'
time_format = '%m/%d/%Y %H:%M'


class Application(DrivenApplicationBaseClass):

    '''
    HVAC economizer diagnostic
    '''
    '''Diagnostic Point Names (Must match OpenEIS data-type names)'''
    fan_status_name = 'fan_status'
    oa_temp_name = 'oa_temp'
    ma_temp_name = 'ma_temp'
    ra_temp_name = 'ra_temp'
    damper_signal_name = 'damper_signal'
    cool_call_name = 'cool_call'

    def __init__(self, *args, economizer_type='DDB', econ_hl_temp=60.0,
                 device_type='AHU', temp_deadband=1.0,
                 data_window=15, no_required_data=10,
                 open_damper_time=5,
                 mat_low_threshold=50.0, mat_high_threshold=90.0,
                 oat_low_threshold=30.0, oat_high_threshold=100.0,
                 rat_low_threshold=50.0, rat_high_threshold=90.0,
                 temp_difference_threshold=4.0, oat_mat_check=5.0,
                 open_damper_threshold=90.0, oaf_economizing_threshold=25.0,
                 oaf_temperature_threshold=4.0,
                 cooling_enabled_threshold=5.0,
                 minimum_damper_setpoint=20, excess_damper_threshold=15.0,
                 excess_oaf_threshold=30.0, desired_oaf=5.0,
                 ventilation_oaf_threshold=5.0,
                 insufficient_damper_threshold=15.0,
                 temp_damper_threshold=90.0, tonnage=None, eer=10.0,
                 data_sample_rate=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fan_status_name = Application.fan_status_name
        self.oa_temp_name = Application.oa_temp_name
        self.ra_temp_name = Application.ra_temp_name
        self.ma_temp_name = Application.ma_temp_name
        self.damper_signal_name = Application.damper_signal_name
        self.cool_call_name = Application.cool_call_name

        self.device_type = device_type.lower()

        self.economizer_type = economizer_type.lower()
        if self.economizer_type == 'hl':
            self.econ_hl_temp = float(econ_hl_temp)

        Application.pre_requiste_messages = []
        Application.pre_msg_time = []
        self.oaf_temperature_threshold = float(oaf_temperature_threshold)

        '''Application thresholds (Configurable)'''
        self.data_window = float(data_window)
        no_required_data = int(no_required_data)
        self.mat_low_threshold = float(mat_low_threshold)
        self.mat_high_threshold = float(mat_high_threshold)
        self.oat_low_threshold = float(oat_low_threshold)
        self.oat_high_threshold = float(oat_high_threshold)
        self.rat_low_threshold = float(rat_low_threshold)
        self.rat_high_threshold = float(rat_high_threshold)
        self.temp_deadband = float(temp_deadband)
        self.cooling_enabled_threshold = float(cooling_enabled_threshold)
        cfm = float(tonnage) * 400.0

        '''Pre-requisite messages'''
        self.pre_msg1 = ('Supply fan is off, current data will '
                         'not be used for diagnostics.')
        self.pre_msg2 = ('Supply fan status data is missing '
                         'from input(device or csv), could '
                         'not verify system was ON.')
        self.pre_msg3 = ('Missing required data for diagnostic: '
                         'Check BACnet configuration or CSV file '
                         'input for outside-air temperature.')
        self.pre_msg4 = ('Missing required data for diagnostic: '
                         'Check BACnet configuration or CSV file '
                         'input for return-air temperature.')
        self.pre_msg5 = ('Missing required data for diagnostic: '
                         'Check BACnet configuration or CSV '
                         'file input for mixed-air temperature.')
        self.pre_msg6 = ('Missing required data for diagnostic: '
                         'Check BACnet configuration or CSV '
                         'file input for damper signal.')
        self.pre_msg7 = ''.join(['Missing required data for diagnostic: ',
                                 'Check BACnet configuration or CSV file '
                                 'input for cooling call (AHU cooling coil,'
                                 'RTU cooling call or compressor command).'])
        self.pre_msg8 = ('Outside-air temperature is outside high/low '
                         'operating limits, check the functionality of '
                         'the temperature sensor.')

        self.pre_msg9 = ('Return-air temperature is outside high/low '
                         'operating limits, check the functionality of '
                         'the temperature sensor.')

        self.pre_msg10 = ('Mixed-air temperature is outside high/low '
                          'operating limits, check the functionality '
                          'of the temperature sensor.')

        self.econ1 = temperature_sensor_dx(data_window, no_required_data,
                                           temp_difference_threshold,
                                           open_damper_time,
                                           oat_mat_check,
                                           temp_damper_threshold,
                                           data_sample_rate)
        self.econ2 = econ_correctly_on(oaf_economizing_threshold,
                                       open_damper_threshold,
                                       self.economizer_type, data_window,
                                       no_required_data, cfm, eer,
                                       data_sample_rate)
        self.econ3 = econ_correctly_off(device_type, self.economizer_type,
                                        data_window, no_required_data,
                                        minimum_damper_setpoint,
                                        excess_damper_threshold,
                                        cooling_enabled_threshold,
                                        desired_oaf, cfm, eer,
                                        data_sample_rate)
        self.econ4 = excess_oa_intake(self.economizer_type, device_type,
                                      data_window, no_required_data,
                                      excess_oaf_threshold,
                                      minimum_damper_setpoint,
                                      excess_damper_threshold,
                                      desired_oaf, cfm, eer,
                                      data_sample_rate)
        self.econ5 = insufficient_oa_intake(device_type, self.economizer_type,
                                            data_window, no_required_data,
                                            ventilation_oaf_threshold,
                                            minimum_damper_setpoint,
                                            insufficient_damper_threshold,
                                            desired_oaf, data_sample_rate)

    @classmethod
    def get_config_parameters(cls):
        '''
        Generate required configuration
        parameters with description for user
        '''
        return {

            'data_sample_rate': ConfigDescriptor(float, 'Data Sampling interval '
                                                 '(minutes/sample)'),
            'tonnage': ConfigDescriptor(float,
                                        'AHU/RTU cooling capacity in tons'),

            'data_window': ConfigDescriptor(int, 'Minimum Elapsed time for '
                                            'analysis (default=15 minutes)',
                                            optional=True),
            'open_damper_time': ConfigDescriptor(float, 'Delay time for '
                                                 'steady-state conditions '
                                                 '(default=5 minutes)',
                                                 optional=True),
            'no_required_data': ConfigDescriptor(int,
                                                 'Number of required '
                                                 'data measurements to '
                                                 'perform diagnostic (10)',
                                                 optional=True),
            'mat_low_threshold': ConfigDescriptor(float,
                                                  'Mixed-air sensor '
                                                  'low limit (default=50F)',
                                                  optional=True),
            'mat_high_threshold': ConfigDescriptor(float,
                                                   'Mixed-air sensor '
                                                   'high limit (default=90F)',
                                                   optional=True),
            'rat_low_threshold': ConfigDescriptor(float,
                                                  'Return-air sensor '
                                                  'low limit (default=50F)',
                                                  optional=True),
            'rat_high_threshold': ConfigDescriptor(float,
                                                   'Return-air sensor '
                                                   'high limit (default=90F)',
                                                   optional=True),
            'oat_low_threshold': ConfigDescriptor(float,
                                                  'Outdoor-air sensor '
                                                  'low limit (default=30F)',
                                                  optional=True),
            'oat_high_threshold': ConfigDescriptor(float,
                                                   'Outdoor-air sensor '
                                                   'high limit (default=100F)',
                                                   optional=True),
            'temp_deadband': ConfigDescriptor(float,
                                              'Economizer control '
                                              'temperature dead-band '
                                              '(default=1F)',
                                              optional=True),
            'minimum_damper_setpoint': ConfigDescriptor(float,
                                                        'Minimum outdoor-air '
                                                        'damper set point '
                                                        '(default=20%)',
                                                        optional=True),
            'excess_damper_threshold': ConfigDescriptor(float,
                                                        'Value above the '
                                                        'minimum damper '
                                                        'set point at which '
                                                        'a fault will be '
                                                        'called (default=15%)',
                                                        optional=True),
            'econ_hl_temp': ConfigDescriptor(float,
                                             'High limit (HL) temperature '
                                             'for HL type economizer '
                                             '(default=60F)',
                                             optional=True),
            'cooling_enabled_threshold': ConfigDescriptor(float,
                                                          'Amount AHU chilled '
                                                          'water valve '
                                                          'must be '
                                                          'open to consider '
                                                          'unit in cooling '
                                                          'mode (default=5%)',
                                                          optional=True),
            'insufficient_damper_threshold': ConfigDescriptor(float,
                                                              'Value below '
                                                              'the minimum '
                                                              'outdoor-air '
                                                              'damper set-'
                                                              'point at which '
                                                              'a fault will '
                                                              'be identified '
                                                              '(default=15%)',
                                                              optional=True),
            'ventilation_oaf_threshold':  ConfigDescriptor(float,
                                                           'The value below '
                                                           'the desired '
                                                           'minimum OA '
                                                           '% where '
                                                           'a fault will be '
                                                           'indicated '
                                                           '(default=5%)',
                                                           optional=True),
            'desired_oaf':  ConfigDescriptor(float,
                                             'The desired minimum OA percent '
                                             '(default=10%)', optional=True),
            'excess_oaf_threshold':  ConfigDescriptor(float,
                                                      'The value above the '
                                                      'desired OA % where a '
                                                      'fault will be '
                                                      'indicated '
                                                      '(default=30%)',
                                                      optional=True),
            'economizer_type': ConfigDescriptor(str,
                                                'Economizer type:  <DDB> - '
                                                'differential dry bulb <HL> - '
                                                'High limit (default=DDB)',
                                                optional=True),
            'open_damper_threshold': ConfigDescriptor(float,
                                                      'Threshold '
                                                      'in which damper is '
                                                      'considered open for '
                                                      'economizing '
                                                      '(default=80%)',
                                                      optional=True),
            'oaf_economizing_threshold': ConfigDescriptor(float,
                                                          'Value below 100% '
                                                          'in which the OA '
                                                          'is considered '
                                                          'insufficient for '
                                                          'economizing '
                                                          '(default=25%)',
                                                          optional=True),
            'oaf_temperature_threshold': ConfigDescriptor(float,
                                                          'Required difference'
                                                          ' between OAT and '
                                                          'RAT for accurate '
                                                          'diagnostic '
                                                          '(default=5F)',
                                                          optional=True),
            'device_type': ConfigDescriptor(str,
                                            'Device type <RTU> or <AHU> '
                                            '(default=AHU)',
                                            optional=True),
            'temp_difference_threshold': ConfigDescriptor(float,
                                                          'Threshold for '
                                                          'detecting '
                                                          'temperature sensor '
                                                          'problems '
                                                          '(default=4F)',
                                                          optional=True),
            'oat_mat_check': ConfigDescriptor(float,
                                              'Temperature threshold for '
                                              'OAT and MAT '
                                              'consistency check for times '
                                              'when the damper is near 100% '
                                              'open (default=5F)',
                                              optional=True),
            'temp_damper_threshold': ConfigDescriptor(float,
                                                      'Damper position to '
                                                      'check for OAT/MAT '
                                                      'consistency '
                                                      '(default=90%)',
                                                      optional=True),
            'eer': ConfigDescriptor(float, 'AHU/RTU rated EER (default=10)',
                                           optional=True),
            }

    @classmethod
    def get_app_descriptor(cls):
        name = 'economizer_rcx'
        desc = 'Automated Retro-commisioning for HVAC Economizer Systems'
        return ApplicationDescriptor(app_name=name, description=desc)

    @classmethod
    def required_input(cls):
        '''
        Generate required inputs with description for
        user
        '''
        return {
            cls.fan_status_name: InputDescriptor('SupplyFanStatus',
                                                 'AHU Supply Fan Status',
                                                 count_min=1),
            cls.oa_temp_name: InputDescriptor('OutdoorAirTemperature',
                                              'AHU or building outdoor-air '
                                              'temperature', count_min=1),
            cls.ma_temp_name: InputDescriptor('MixedAirTemperature',
                                              'AHU mixed-air temperature',
                                              count_min=1),
            cls.ra_temp_name: InputDescriptor('ReturnAirTemperature',
                                              'AHU return-air temperature',
                                              count_min=1),
            cls.damper_signal_name: InputDescriptor('OutdoorDamperSignal',
                                                    'AHU outdoor-air damper '
                                                    'signal', count_min=1),
            cls.cool_call_name: InputDescriptor('CoolingCall',
                                                'AHU cooling coil command or '
                                                'RTU coolcall or compressor '
                                                'command', count_min=1)
        }

    def reports(self):
        '''
        Called by UI to create Viz.
        Describe how to present output to user
        Display this viz with these columns from this table

        display_elements is a list of display
        objects specifying viz and columns
        for that viz
        '''
        return []

    @classmethod
    def output_format(cls, input_object):
        '''
        Called when application is staged.
        Output will have the date-time and  error-message.
        '''
        result = super().output_format(input_object)

        topics = input_object.get_topics()
        diagnostic_topic = topics[cls.fan_status_name][0]
        diagnostic_topic_parts = diagnostic_topic.split('/')
        output_topic_base = diagnostic_topic_parts[:-1]
        datetime_topic = '/'.join(output_topic_base +
                                  ['Economizer_RCx', 'date'])
        message_topic = '/'.join(output_topic_base +
                                 ['Economizer_RCx', 'message'])
        diagnostic_name = '/'.join(output_topic_base +
                                   ['Economizer_RCx', 'diagnostic_name'])
        energy_impact = '/'.join(output_topic_base +
                                 ['Economizer_RCx', 'energy_impact'])
        color_code = '/'.join(output_topic_base +
                              ['Economizer_RCx', 'color_code'])

        output_needs = {
            'Economizer_RCx': {
                'datetime': OutputDescriptor('datetime', datetime_topic),
                'diagnostic_name': OutputDescriptor('string', diagnostic_name),
                'diagnostic_message': OutputDescriptor('string',
                                                       message_topic),
                'energy_impact': OutputDescriptor('float', energy_impact),
                'color_code': OutputDescriptor('string', color_code)
            }
        }
        result.update(output_needs)
        return result

    def run(self, current_time, points):
        '''
        Check application pre-quisites and assemble data set for analysis.
        '''
        device_dict = {}
        diagnostic_result = Results()

        for key, value in points.items():
            device_dict[key.lower()] = value

        Application.pre_msg_time.append(current_time)
        message_check = datetime.timedelta(minutes=(self.data_window))
        pre_time = (Application.pre_msg_time[-1] - Application.pre_msg_time[0])
        if pre_time >= message_check:
            msg_lst = [self.pre_msg1, self.pre_msg2,
                       self.pre_msg3, self.pre_msg4,
                       self.pre_msg5, self.pre_msg6,
                       self.pre_msg7, self.pre_msg8,
                       self.pre_msg9, self.pre_msg10]
            for item in msg_lst:
                if (Application.pre_requiste_messages.count(item) >
                        (0.25) * len(Application.pre_msg_time)):
                    diagnostic_result.log(item, logging.DEBUG)
            Application.pre_requiste_messages = []
            Application.pre_msg_time = []

        fan_stat_check = False
        for key, value in device_dict.items():
            if key.startswith(self.fan_status_name):
                if value is not None and not int(value):
                    Application.pre_requiste_messages.append(self.pre_msg1)
                    return diagnostic_result
                elif value is not None:
                    fan_stat_check = True
        if not fan_stat_check:
            Application.pre_requiste_messages.append(self.pre_msg2)
            return diagnostic_result

        damper_data = []
        oatemp_data = []
        matemp_data = []
        ratemp_data = []
        cooling_data = []

        for key, value in device_dict.items():
            if (key.startswith(self.damper_signal_name)
                    and value is not None):
                damper_data.append(value)

            elif (key.startswith(self.oa_temp_name)
                  and value is not None):
                oatemp_data.append(value)

            elif (key.startswith(self.ma_temp_name)
                  and value is not None):
                matemp_data.append(value)

            elif (key.startswith(self.ra_temp_name)
                  and value is not None):
                ratemp_data.append(value)

            elif (key.startswith(self.cool_call_name)
                  and value is not None):
                cooling_data.append(value)

        if not oatemp_data:
            Application.pre_requiste_messages.append(self.pre_msg3)

        if not ratemp_data:
            Application.pre_requiste_messages.append(self.pre_msg4)

        if not matemp_data:
            Application.pre_requiste_messages.append(self.pre_msg5)

        if not damper_data:
            Application.pre_requiste_messages.append(self.pre_msg6)

        if not cooling_data:
            Application.pre_requiste_messages.append(self.pre_msg7)

        if not (oatemp_data and ratemp_data and matemp_data and
                damper_data and cooling_data):
            return diagnostic_result

        oatemp = (sum(oatemp_data) / len(oatemp_data))
        ratemp = (sum(ratemp_data) / len(ratemp_data))
        matemp = (sum(matemp_data) / len(matemp_data))
        damper_signal = (sum(damper_data) / len(damper_data))

        limit_check = False
        if oatemp < self.oat_low_threshold or oatemp > self.oat_high_threshold:
            Application.pre_requiste_messages.append(self.pre_msg8)
            limit_check = True
        if ratemp < self.rat_low_threshold or ratemp > self.rat_high_threshold:
            Application.pre_requiste_messages.append(self.pre_msg9)
            limit_check = True
        if matemp < self.mat_low_threshold or matemp > self.mat_high_threshold:
            Application.pre_requiste_messages.append(self.pre_msg10)
            limit_check = True

        if limit_check:
            return diagnostic_result

        if abs(oatemp - ratemp) < self.oaf_temperature_threshold:
            diagnostic_result.log('OAT and RAT are too close, economizer '
                                  'diagnostic will not use data '
                                  'corresponding to: {timestamp} '
                                  .format(timestamp=str(current_time)),
                                  logging.DEBUG)
            return diagnostic_result

        device_type_error = False
        if self.device_type == 'ahu':
            cooling_valve = sum(cooling_data) / len(cooling_data)
            if cooling_valve > self.cooling_enabled_threshold:
                cooling_call = True
            else:
                cooling_call = False
        elif self.device_type == 'rtu':
            cooling_call = int(max(cooling_data))
        else:
            device_type_error = True
            diagnostic_result.log('device_type must be specified '
                                  'as "AHU" or "RTU" Check '
                                  'Configuration input.', logging.INFO)

        if device_type_error:
            return diagnostic_result

        if self.economizer_type == 'ddb':
            economizer_conditon = (oatemp < (ratemp - self.temp_deadband))
        else:
            economizer_conditon = (
                oatemp < (self.econ_hl_temp - self.temp_deadband))

        diagnostic_result = self.econ1.econ_alg1(diagnostic_result,
                                                 cooling_call, oatemp, ratemp,
                                                 matemp, damper_signal,
                                                 current_time)

        if (temperature_sensor_dx.temp_sensor_problem is not None and
           temperature_sensor_dx.temp_sensor_problem is False):
            diagnostic_result = self.econ2.econ_alg2(diagnostic_result,
                                                     cooling_call, oatemp,
                                                     ratemp, matemp,
                                                     damper_signal,
                                                     economizer_conditon,
                                                     current_time)
            diagnostic_result = self.econ3.econ_alg3(diagnostic_result,
                                                     cooling_call,
                                                     oatemp, ratemp,
                                                     matemp, damper_signal,
                                                     economizer_conditon,
                                                     current_time)
            diagnostic_result = self.econ4.econ_alg4(diagnostic_result,
                                                     cooling_call,
                                                     oatemp, ratemp,
                                                     matemp, damper_signal,
                                                     economizer_conditon,
                                                     current_time)
            diagnostic_result = self.econ5.econ_alg5(diagnostic_result,
                                                     cooling_call,
                                                     oatemp, ratemp,
                                                     matemp, damper_signal,
                                                     economizer_conditon,
                                                     current_time)
        else:
            diagnostic_result = self.econ2.clear_data(diagnostic_result)
            diagnostic_result = self.econ3.clear_data(diagnostic_result)
            diagnostic_result = self.econ4.clear_data(diagnostic_result)
            diagnostic_result = self.econ5.clear_data(diagnostic_result)
            temperature_sensor_dx.temp_sensor_problem = None
        return diagnostic_result


class temperature_sensor_dx(object):

    '''
    Air-side HVAC diagnostic to check the functionality of
    the air temperature sensors in an AHU/RTU.
    '''

    def __init__(self, data_window, no_required_data,
                 temp_difference_threshold, open_damper_time,
                 oat_mat_check, temp_damper_threshold,
                 data_sample_rate):
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.timestamp = []
        self.open_damper_oat = []
        self.open_damper_mat = []
        self.econ_check = False
        self.steady_state_start = None
        self.data_sample_rate = float(data_sample_rate)
        self.open_damper_time = int(open_damper_time)
        self.econ_time_check = datetime.timedelta(
            minutes=self.open_damper_time - 1)
        temperature_sensor_dx.temp_sensor_problem = None

        '''Application thresholds (Configurable)'''
        self.data_window = float(data_window)
        self.no_required_data = no_required_data
        self.temp_difference_threshold = float(temp_difference_threshold)
        self.oat_mat_check = float(oat_mat_check)
        self.temp_damper_threshold = float(temp_damper_threshold)

    def econ_alg1(self, diagnostic_result, cooling_call, oatemp,
                  ratemp, matemp, damper_signal, current_time):
        '''
        Check application pre-quisites and assemble data set for analysis.
        '''
        if (damper_signal) > self.temp_damper_threshold:
            if not self.econ_check:
                self.econ_check = True
                self.steady_state_start = current_time
            if ((current_time - self.steady_state_start)
               >= self.econ_time_check):
                self.open_damper_oat.append(oatemp)
                self.open_damper_mat.append(matemp)
        else:
            self.econ_check = False

        self.oa_temp_values.append(oatemp)
        self.ma_temp_values.append(matemp)
        self.ra_temp_values.append(ratemp)
        self.timestamp.append(current_time)

        time_check = datetime.timedelta(minutes=(self.data_window))

        elapsed_time = ((self.timestamp[-1] - self.timestamp[0]) +
                        datetime.timedelta(minutes=self.data_sample_rate))

        if (elapsed_time >= time_check and
                len(self.timestamp) >= self.no_required_data):
            diagnostic_result = self.temperature_sensor_dx(
                diagnostic_result, current_time)
        return diagnostic_result

    def temperature_sensor_dx(self, result, current_time):
        '''
        If the detected problems(s) are
        consistent then generate a fault message(s).
        '''
        oa_ma = [(x - y)
                 for x, y in zip(self.oa_temp_values, self.ma_temp_values)]
        ra_ma = [(x - y)
                 for x, y in zip(self.ra_temp_values, self.ma_temp_values)]
        ma_oa = [(y - x)
                 for x, y in zip(self.oa_temp_values, self.ma_temp_values)]
        ma_ra = [(y - x)
                 for x, y in zip(self.ra_temp_values, self.ma_temp_values)]
        avg_oa_ma = sum(oa_ma) / len(oa_ma)
        avg_ra_ma = sum(ra_ma) / len(ra_ma)
        avg_ma_oa = sum(ma_oa) / len(ma_oa)
        avg_ma_ra = sum(ma_ra) / len(ma_ra)
        color_code = 'GREEN'
        Application.pre_requiste_messages = []
        Application.pre_msg_time = []
        dx_table = {}

        if len(self.open_damper_oat) > self.no_required_data:
            mat_oat_diff_list = [
                abs(x - y)for x, y in zip(self.open_damper_oat,
                                          self.open_damper_mat)]
            open_damper_check = sum(mat_oat_diff_list) / len(mat_oat_diff_list)

            if open_damper_check > self.oat_mat_check:
                temperature_sensor_dx.temp_sensor_problem = True
                diagnostic_message = ('{name}: OAT and MAT and sensor '
                                      'readings are not consistent '
                                      'when the outdoor-air damper '
                                      'is fully open.'.format(name=econ1))
                color_code = 'RED'
                dx_table = {
                    'datetime': str(current_time),
                    'diagnostic_name': econ1,
                    'diagnostic_message': diagnostic_message,
                    'energy_impact': None,
                    'color_code': color_code
                }
                result.log(diagnostic_message, logging.INFO)
                result.insert_table_row('Economizer_RCx', dx_table)
            self.open_damper_oat = []
            self.open_damper_mat = []

        if ((avg_oa_ma) > self.temp_difference_threshold and
                (avg_ra_ma) > self.temp_difference_threshold):
            diagnostic_message = ('{name}: Temperature sensor problem '
                                  'detected. Mixed-air temperature is '
                                  'less than outdoor-air and return-air'
                                  'temperature.'.format(name=econ1))

            color_code = 'RED'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ1,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
            temperature_sensor_dx.temp_sensor_problem = True

        elif((avg_ma_oa) > self.temp_difference_threshold and
             (avg_ma_ra) > self.temp_difference_threshold):
            diagnostic_message = ('{name}: Temperature sensor problem '
                                  'detected Mixed-air temperature is '
                                  'greater than outdoor-air and return-air '
                                  'temperature.'.format(name=econ1))
            temperature_sensor_dx.temp_sensor_problem = True
            color_code = 'RED'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ1,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }

        elif (temperature_sensor_dx.temp_sensor_problem is None
              or not temperature_sensor_dx.temp_sensor_problem):
            diagnostic_message = '{name}: No problems were detected.'.format(
                name=econ1)
            temperature_sensor_dx.temp_sensor_problem = False
            color_code = 'GREEN'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ1,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
        else:
            diagnostic_message = '{name}: Diagnostic was inconclusive'.format(
                name=econ1)
            temperature_sensor_dx.temp_sensor_problem = False
            color_code = 'GREEN'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ1,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
        result.insert_table_row('Economizer_RCx', dx_table)
        result.log(diagnostic_message, logging.INFO)
        result = self.clear_data(result)
        return result

    def clear_data(self, diagnostic_result):
        '''
        reinitialize class insufficient_oa data
        '''
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.timestamp = []
        return diagnostic_result


class econ_correctly_on(object):

    '''
    Air-side HVAC diagnostic to check
    if an AHU/RTU is not economizing
    when it should.
    '''

    def __init__(self, oaf_economizing_threshold, open_damper_threshold,
                 economizer_type, data_window, no_required_data, cfm, eer,
                 data_sample_rate):

        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.damper_signal_values = []
        self.timestamp = []
        self.output_no_run = []
        self.economizer_type = economizer_type
        self.open_damper_threshold = float(open_damper_threshold)
        self.oaf_economizing_threshold = float(oaf_economizing_threshold)
        self.data_window = float(data_window)
        self.no_required_data = no_required_data
        self.cfm = cfm
        self.eer = float(eer)
        self.data_sample_rate = float(data_sample_rate)

        '''Application result messages'''
        self.alg_result_messages = ['{name}: Conditions are favorable for '
                                    'economizing but the damper is frequently '
                                    'below 100% open.'.format(name=econ2),
                                    '{name}: No problems detected.'.format(
                                        name=econ2),
                                    '{name}: Conditions are favorable for '
                                    'economizing and the damper is 100% '
                                    'open but the OAF indicates the unit '
                                    'is not brining in near 100% OA.'.format(
                                        name=econ2)]

    def econ_alg2(self, diagnostic_result, cooling_call, oatemp, ratemp,
                  matemp, damper_signal, economizer_conditon, current_time):
        if not cooling_call:
            diagnostic_result.log('The unit is not cooling, data '
                                  'corresponding to {timestamp} will '
                                  'not be used for {name} diagnostic.'.
                                  format(timestamp=str(current_time),
                                         name=econ2), logging.DEBUG)
            self.output_no_run.append(current_time)
            if ((self.output_no_run[-1] - self.output_no_run[0]) >=
               datetime.timedelta(minutes=(self.data_window))):
                diagnostic_result.log(('{name}: the unit is not cooling or '
                                      'economizing, keep collecting data.')
                                      .format(name=econ2), logging.DEBUG)
                self.output_no_run = []
            return diagnostic_result

        if not economizer_conditon:
            diagnostic_result.log('{name}: Conditions are not favorable for '
                                  'economizing, data corresponding to '
                                  '{timestamp} will not be used.'.
                                  format(timestamp=str(current_time),
                                         name=econ2), logging.DEBUG)
            self.output_no_run.append(current_time)
            if ((self.output_no_run[-1] - self.output_no_run[0]) >=
               datetime.timedelta(minutes=(self.data_window))):
                diagnostic_result.log(('{name}: the unit is not cooling or '
                                      'economizing, keep collecting data.')
                                      .format(name=econ2), logging.DEBUG)
                self.output_no_run = []
            return diagnostic_result

        self.oa_temp_values.append(oatemp)
        self.ma_temp_values.append(matemp)
        self.ra_temp_values.append(ratemp)
        self.timestamp.append(current_time)
        self.damper_signal_values.append(damper_signal)

        time_check = datetime.timedelta(minutes=(self.data_window))

        elapsed_time = ((self.timestamp[-1] - self.timestamp[0]) +
                        datetime.timedelta(minutes=self.data_sample_rate))

        if (elapsed_time >= time_check and
           len(self.timestamp) >= self.no_required_data):
            diagnostic_result = self.not_economizing_when_needed(
                diagnostic_result, current_time)
        return diagnostic_result

    def not_economizing_when_needed(self, result, current_time):
        '''
        If the detected problems(s) are
        consistent then generate a fault
        message(s).
        '''
        oaf = [(m - r) / (o - r) for o, r, m in zip(self.oa_temp_values,
                                                    self.ra_temp_values,
                                                    self.ma_temp_values)]
        avg_oaf = sum(oaf) / len(oaf) * 100.0
        avg_damper_signal = sum(
            self.damper_signal_values) / len(self.damper_signal_values)
        energy_impact = None

        if avg_damper_signal < self.open_damper_threshold:
            diagnostic_message = (self.alg_result_messages[0])
            color_code = 'RED'
        else:
            if (100.0 - avg_oaf) <= self.oaf_economizing_threshold:
                diagnostic_message = (self.alg_result_messages[1])
                color_code = 'GREEN'
                energy_impact = None
            else:
                diagnostic_message = (self.alg_result_messages[2])
                color_code = 'RED'

        energy_calc = [(1.08 * self.cfm * (ma - oa) / (1000.0 * self.eer)) for
                       ma, oa in zip(self.ma_temp_values, self.oa_temp_values)
                       if (ma - oa) > 0 and color_code == 'RED']

        if energy_calc:
            dx_time = (len(energy_calc) - 1) * \
                self.data_sample_rate if len(energy_calc) > 1 else 1.0
            energy_impact = (sum(energy_calc) * 60.0) / \
                (len(energy_calc) * dx_time)

        dx_table = {
            'datetime': str(current_time),
            'diagnostic_name': econ2, 'diagnostic_message': diagnostic_message,
            'energy_impact': energy_impact,
            'color_code': color_code
        }
        result.insert_table_row('Economizer_RCx', dx_table)
        result.log(diagnostic_message, logging.INFO)
        result = self.clear_data(result)
        return result

    def clear_data(self, diagnostic_result):
        '''
        reinitialize class insufficient_oa data
        '''
        self.damper_signal_values = []
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.timestamp = []
        return diagnostic_result


class econ_correctly_off(object):

    '''
    Air-side HVAC diagnostic to
    check if an AHU/RTU is economizing
    when it should not.
    '''

    def __init__(self, device_type, economizer_type, data_window,
                 no_required_data, minimum_damper_setpoint,
                 excess_damper_threshold, cooling_enabled_threshold,
                 desired_oaf, cfm, eer, data_sample_rate):
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.damper_signal_values = []
        self.cool_call_values = []
        self.cfm = cfm
        self.eer = float(eer)
        self.data_sample_rate = float(data_sample_rate)
        self.timestamp = []

        '''Application result messages'''
        self.alg_result_messages = ['{name}: The outdoor-air damper should be '
                                    'at the minimum position but is '
                                    'significantly above that value.'
                                    .format(name=econ3),
                                    '{name}: No problems detected.'
                                    .format(name=econ3),
                                    '{name}: The diagnostic led to '
                                    'inconclusive results, could not '
                                    'verify the status of the economizer: '
                                    .format(name=econ3)]
        self.cfm = cfm
        self.eer = float(eer)
        self.data_sample_rate = float(data_sample_rate)
        self.device_type = device_type
        self.data_window = float(data_window)
        self.no_required_data = no_required_data
        self.economizer_type = economizer_type
        self.minimum_damper_setpoint = float(minimum_damper_setpoint)
        self.excess_damper_threshold = float(excess_damper_threshold)
        self.cooling_enabled_threshold = float(cooling_enabled_threshold)
        self.desired_oaf = float(desired_oaf)

    def econ_alg3(self, diagnostic_result, cooling_call, oatemp, ratemp,
                  matemp, damper_signal, economizer_conditon, current_time):
        '''
        Check application pre-quisites and
        economizer conditions (Problem or No Problem).
        '''
        if economizer_conditon:
            diagnostic_result.log(''.join([self.alg_result_messages[2],
                                           (' Data corresponding to '
                                            '{tstamp} will not '
                                            'be used for this diagnostic.'
                                            .format(tstamp=str
                                                    (current_time)))]),
                                  logging.DEBUG)
            return diagnostic_result
        else:
            self.damper_signal_values.append(damper_signal)
            self.oa_temp_values.append(oatemp)
            self.ma_temp_values.append(matemp)
            self.ra_temp_values.append(ratemp)
            self.timestamp.append(current_time)

            time_check = datetime.timedelta(minutes=(self.data_window))
        elapsed_time = ((self.timestamp[-1] - self.timestamp[0]) +
                        datetime.timedelta(minutes=self.data_sample_rate))

        if (elapsed_time >= time_check and
           len(self.timestamp) >= self.no_required_data):
            diagnostic_result = self.economizing_when_not_needed(
                diagnostic_result, current_time)
        return diagnostic_result

    def economizing_when_not_needed(self, result, current_time):
        '''
        If the detected problems(s)
        are consistent then generate a
        fault message(s).
        '''
        desired_oaf = self.desired_oaf / 100.0

        energy_calc = [(1.08 * self.cfm * (ma - (oa * desired_oaf +
                                                 (ra * (1.0 - desired_oaf))))
                        / (1000.0 * self.eer)) for ma, oa, ra in
                       zip(self.ma_temp_values,
                           self.oa_temp_values,
                           self.ra_temp_values)
                       if (ma - (oa * desired_oaf +
                                 (ra * (1.0 - desired_oaf)))) > 0]

        avg_damper = sum(self.damper_signal_values) / \
            len(self.damper_signal_values)

        if ((avg_damper - self.minimum_damper_setpoint)
                > self.excess_damper_threshold):
            diagnostic_message = self.alg_result_messages[0]
            color_code = 'RED'
        else:
            diagnostic_message = '{name}: No problems detected.'.format(
                name=econ3)
            color_code = 'GREEN'
            energy_impact = None

        if energy_calc and color_code == 'RED':
            dx_time = (len(energy_calc) - 1) * \
                self.data_sample_rate if len(energy_calc) > 1 else 1.0
            energy_impact = (sum(energy_calc) * 60.0) / \
                (len(energy_calc) * dx_time)

        dx_table = {'datetime': str(current_time),
                    'diagnostic_name': econ3,
                    'diagnostic_message': diagnostic_message,
                    'energy_impact': energy_impact,
                    'color_code': color_code
                    }

        result.insert_table_row('Economizer_RCx', dx_table)
        result.log(diagnostic_message, logging.INFO)
        result = self.clear_data(result)
        return result

    def clear_data(self, diagnostic_result):
        '''
        reinitialize class insufficient_oa data
        '''
        self.damper_signal_values = []
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.timestamp = []
        return diagnostic_result


class excess_oa_intake(object):

    '''
    Air-side HVAC diagnostic to check
    if an AHU/RTU bringing in excess
    outdoor air.
    '''

    def __init__(self, economizer_type, device_type, data_window,
                 no_required_data, excess_oaf_threshold,
                 minimum_damper_setpoint, excess_damper_threshold,
                 desired_oaf, cfm, eer, data_sample_rate):
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.damper_signal_values = []
        self.cool_call_values = []
        self.timestamp = []
        '''Application thresholds (Configurable)'''
        self.cfm = cfm
        self.eer = float(eer)
        self.data_sample_rate = float(data_sample_rate)
        self.economizer_type = economizer_type
        self.data_window = float(data_window)
        self.no_required_data = no_required_data
        self.excess_oaf_threshold = float(excess_oaf_threshold)
        self.minimum_damper_setpoint = float(minimum_damper_setpoint)
        self.desired_oaf = float(desired_oaf)
        self.excess_damper_threshold = float(excess_damper_threshold)

    def econ_alg4(self, diagnostic_result, cooling_call, oatemp, ratemp,
                  matemp, damper_signal, economizer_conditon, current_time):
        '''
        Check application pre-quisites and assemble
        data set for analysis.
        '''

        if economizer_conditon:
            diagnostic_result.log('{name}: The unit may be economizing, '
                                  'data corresponding to {timestamp} '
                                  'will not be used for this diagnostic.'.
                                  format(timestamp=str(current_time),
                                         name=econ4),
                                  logging.DEBUG)
            return diagnostic_result

        self.damper_signal_values.append(damper_signal)
        self.oa_temp_values.append(oatemp)
        self.ra_temp_values.append(ratemp)
        self.ma_temp_values.append(matemp)
        self.timestamp.append(current_time)

        time_check = datetime.timedelta(minutes=(self.data_window))

        elapsed_time = ((self.timestamp[-1] - self.timestamp[0]) +
                        datetime.timedelta(minutes=self.data_sample_rate))

        if (elapsed_time >= time_check and
           len(self.timestamp) >= self.no_required_data):
            diagnostic_result = self.excess_oa(diagnostic_result, current_time)
        return diagnostic_result

    def excess_oa(self, result, current_time):
        '''
        If the detected problems(s) are
        consistent then generate a fault message(s).
        '''
        oaf = [(m - r) / (o - r) for o, r, m in zip(self.oa_temp_values,
                                                    self.ra_temp_values,
                                                    self.ma_temp_values)]

        avg_oaf = sum(oaf) / len(oaf) * 100
        avg_damper = sum(self.damper_signal_values) / \
            len(self.damper_signal_values)

        desired_oaf = self.desired_oaf / 100.0
        energy_calc = [(1.08 * self.cfm * (ma - (oa * desired_oaf +
                                                 (ra * (1.0 - desired_oaf))))
                        / (1000.0 * self.eer)) for ma, oa, ra in
                       zip(self.ma_temp_values,
                           self.oa_temp_values,
                           self.ra_temp_values)
                       if (ma - (oa * desired_oaf +
                                 (ra * (1.0 - desired_oaf)))) > 0]
        diagnostic_message = '{name}: Inconclusive diagnostic.'.format(
            name=econ4)
        color_code = 'GREY'
        energy_impact = None

        if avg_oaf < 0 or avg_oaf > 125.0:
            diagnostic_message = ('{name}: Inconclusive result, the OAF '
                                  'calculation led to an '
                                  'unexpected value: {oaf}'.
                                  format(name=econ4, oaf=avg_oaf))
            color_code = 'GREY'
            result.log(diagnostic_message, logging.INFO)
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ4,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
            result.insert_table_row('Economizer_RCx', dx_table)
            result = self.clear_data(result)
            return result

        if ((avg_damper - self.minimum_damper_setpoint)
                > self.excess_damper_threshold):
            diagnostic_message = ('{name}: The damper should be at the '
                                  'minimum position for ventilation but '
                                  'is significantly higher than this value.'.
                                  format(name=econ4))
            color_code = 'RED'

            if energy_calc:
                dx_time = (len(energy_calc) - 1) * \
                    self.data_sample_rate if len(energy_calc) > 1 else 1.0
                energy_impact = (sum(energy_calc) * 60.0) / \
                    (len(energy_calc) * dx_time)
        if avg_oaf - self.desired_oaf > self.excess_oaf_threshold:
            if diagnostic_message:
                diagnostic_message += ('Excess outdoor-air is being '
                                       'provided, this could increase '
                                       'heating and cooling energy '
                                       'consumption.'.format(name=econ4))
            else:
                diagnostic_message = ('{name}: Excess outdoor-air is being '
                                      'provided, this could increase '
                                      'heating and cooling energy '
                                      'consumption.'.format(name=econ4))
            color_code = 'RED'

            if energy_calc:
                dx_time = (len(energy_calc) - 1) * \
                    self.data_sample_rate if len(energy_calc) > 1 else 1.0
                energy_impact = (sum(energy_calc) * 60.0) / \
                    (len(energy_calc) * dx_time)

        elif not diagnostic_message:
            diagnostic_message = ('{name}: The calculated outdoor-air '
                                  'fraction is within configured '
                                  'limits'.format(name=econ4))
            color_code = 'GREEN'

        dx_table = {
            'datetime': str(current_time),
            'diagnostic_name': econ4,
            'diagnostic_message': diagnostic_message,
            'energy_impact': energy_impact,
            'color_code': color_code
        }
        result.insert_table_row('Economizer_RCx', dx_table)
        result.log(diagnostic_message, logging.INFO)

        result = self.clear_data(result)
        return result

    def clear_data(self, diagnostic_result):
        '''
        reinitialize class insufficient_oa data
        '''
        self.damper_signal_values = []
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.timestamp = []
        return diagnostic_result


class insufficient_oa_intake(object):

    '''
    Air-side HVAC diagnostic to check if an
    AHU/RTU bringing in insufficient outdoor air.
    '''

    def __init__(self, device_type, economizer_type, data_window,
                 no_required_data, ventilation_oaf_threshold,
                 minimum_damper_setpoint, insufficient_damper_threshold,
                 desired_oaf, data_sample_rate):

        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.damper_signal_values = []
        self.cool_call_values = []
        self.timestamp = []

        '''Application thresholds (Configurable)'''
        self.data_window = float(data_window)
        self.no_required_data = no_required_data
        self.data_sample_rate = float(data_sample_rate)
        self.ventilation_oaf_threshold = float(ventilation_oaf_threshold)
        self.insufficient_damper_threshold = float(
            insufficient_damper_threshold)
        self.minimum_damper_setpoint = float(minimum_damper_setpoint)
        self.desired_oaf = float(desired_oaf)

    def econ_alg5(self, diagnostic_result, cooling_call, oatemp,
                  ratemp, matemp, damper_signal, economizer_conditon,
                  current_time):
        '''
        Check application pre-quisites and assemble data set for analysis.
        '''
        if economizer_conditon:
            diagnostic_result.log('{name}: The unit may be economizing, '
                                  'data corresponding to {timestamp}'
                                  ' will not be used for the diagnostic.'
                                  .format(timestamp=str(current_time),
                                          name=econ5), logging.DEBUG)
            return diagnostic_result

        self.oa_temp_values.append(oatemp)
        self.ra_temp_values.append(ratemp)
        self.ma_temp_values.append(matemp)
        self.timestamp.append(current_time)
        self.damper_signal_values.append(damper_signal)

        time_check = datetime.timedelta(minutes=(self.data_window))

        elapsed_time = ((self.timestamp[-1] - self.timestamp[0]) +
                        datetime.timedelta(minutes=self.data_sample_rate))

        if (elapsed_time >= time_check and
           len(self.timestamp) >= self.no_required_data):
            diagnostic_result = self.insufficient_oa(
                diagnostic_result, current_time)
        return diagnostic_result

    def insufficient_oa(self, result, current_time):
        '''
        If the detected problems(s) are
        consistent then generate a fault message(s).
        '''
        oaf = [(m - r) / (o - r) for o, r, m in zip(self.oa_temp_values,
                                                    self.ra_temp_values,
                                                    self.ma_temp_values)]
        avg_oaf = sum(oaf) / len(oaf) * 100.0
        avg_damper_signal = (sum(
            self.damper_signal_values) / len(self.damper_signal_values))

        if avg_oaf < 0 or avg_oaf > 125.0:
            diagnostic_message = ('{name}: Inconclusive result, the OAF '
                                  'calculation led to an '
                                  'unexpected value: {oaf}'.
                                  format(name=econ5, oaf=avg_oaf))
            color_code = 'GREY'
            result.log(diagnostic_message, logging.INFO)
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ4,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
            result.insert_table_row('Economizer_RCx', dx_table)
            result = self.clear_data(result)
            return result

        diagnostic_message = []
        if (
                (self.minimum_damper_setpoint - avg_damper_signal) >
                self.insufficient_damper_threshold):
            diagnostic_message = ('{name}: Outdoor-air damper is '
                                  'significantly below the minimum '
                                  'configured damper position.'
                                  .format(name=econ5))

            color_code = 'RED'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ5,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
            result.insert_table_row('Economizer_RCx', dx_table)
            result = self.clear_data(result)
            return result

        if (self.desired_oaf - avg_oaf) > self.ventilation_oaf_threshold:
            diagnostic_message = ('{name}: Insufficient outdoor-air '
                                  'is being provided for '
                                  'ventilation.'.format(name=econ5))
            color_code = 'RED'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ5,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }
        else:
            diagnostic_message = ('{name}: The calculated outdoor-air'
                                  'fraction was within acceptable '
                                  'limits.'.format(name=econ5))
            color_code = 'GREEN'
            dx_table = {
                'datetime': str(current_time),
                'diagnostic_name': econ5,
                'diagnostic_message': diagnostic_message,
                'energy_impact': None,
                'color_code': color_code
            }

        result.insert_table_row('Economizer_RCx', dx_table)
        result.log(diagnostic_message, logging.INFO)
        Application.pre_msg_time = []
        Application.pre_requiste_messages = []
        result = self.clear_data(result)
        return result

    def clear_data(self, diagnostic_result):
        '''
        reinitialize class insufficient_oa data
        '''
        self.damper_signal_values = []
        self.oa_temp_values = []
        self.ra_temp_values = []
        self.ma_temp_values = []
        self.timestamp = []
        return diagnostic_result