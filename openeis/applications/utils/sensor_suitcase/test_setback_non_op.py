"""
Unit test `setback_non_op.py`.


Copyright
=========

OpenEIS Algorithms Phase 2 Copyright (c) 2014,
The Regents of the University of California, through Lawrence Berkeley National
Laboratory (subject to receipt of any required approvals from the U.S.
Department of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Technology Transfer Department at TTD@lbl.gov
referring to "OpenEIS Algorithms Phase 2 (LBNL Ref 2014-168)".

NOTICE:  This software was produced by The Regents of the University of
California under Contract No. DE-AC02-05CH11231 with the Department of Energy.
For 5 years from November 1, 2012, the Government is granted for itself and
others acting on its behalf a nonexclusive, paid-up, irrevocable worldwide
license in this data to reproduce, prepare derivative works, and perform
publicly and display publicly, by or on behalf of the Government. There is
provision for the possible extension of the term of this license. Subsequent to
that period or any extension granted, the Government is granted for itself and
others acting on its behalf a nonexclusive, paid-up, irrevocable worldwide
license in this data to reproduce, prepare derivative works, distribute copies
to the public, perform publicly and display publicly, and to permit others to
do so. The specific term of the license can be identified by inquiry made to
Lawrence Berkeley National Laboratory or DOE. Neither the United States nor the
United States Department of Energy, nor any of their employees, makes any
warranty, express or implied, or assumes any legal liability or responsibility
for the accuracy, completeness, or usefulness of any data, apparatus, product,
or process disclosed, or represents that its use would not infringe privately
owned rights.


License
=======

Copyright (c) 2014, The Regents of the University of California, Department
of Energy contract-operators of the Lawrence Berkeley National Laboratory.
All rights reserved.

1. Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions are met:

   (a) Redistributions of source code must retain the copyright notice, this
   list of conditions and the following disclaimer.

   (b) Redistributions in binary form must reproduce the copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

   (c) Neither the name of the University of California, Lawrence Berkeley
   National Laboratory, U.S. Dept. of Energy nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

2. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
   DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
   ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
   ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
   THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

3. You are under no obligation whatsoever to provide any bug fixes, patches,
   or upgrades to the features, functionality or performance of the source code
   ("Enhancements") to anyone; however, if you choose to make your Enhancements
   available either publicly, or directly to Lawrence Berkeley National
   Laboratory, without imposing a separate written license agreement for such
   Enhancements, then you hereby grant the following license: a non-exclusive,
   royalty-free perpetual license to install, use, modify, prepare derivative
   works, incorporate into other computer software, distribute, and sublicense
   such enhancements or derivative works thereof, in binary and source code
   form.

NOTE: This license corresponds to the "revised BSD" or "3-clause BSD" license
and includes the following modification: Paragraph 3. has been added.
"""


from openeis.applications.utest_applications.apptest import AppTestBase
from openeis.applications.utils.testing_utils import set_up_datetimes, append_data_to_datetime

from openeis.applications.utils.sensor_suitcase.setback_non_op import setback_non_op
import datetime
import copy

class TestComfortAndSetback(AppTestBase):

    def test_setback_success(self):
        # ten data points
        a = datetime.datetime(2014, 1, 1, 0, 0, 0, 0)
        b = datetime.datetime(2014, 1, 3, 6, 0, 0, 0)
        #delta = 6 hours
        base = set_up_datetimes(a, b, 21600)

        # copy data to put in the right format
        DAT = copy.deepcopy(base)
        DAT_temp = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        append_data_to_datetime(DAT, DAT_temp)

        IAT = copy.deepcopy(base)
        IAT_temp = [10, 10, 10, 10, 10, 10, 10, 10, 80, 80]
        append_data_to_datetime(IAT, IAT_temp)

        # the first point is the only operational point
        op_hours = [[0, 1], [3], []]

        result = setback_non_op(IAT, DAT, op_hours, 10000, 5000)

        self.assertEqual(result, {})

    def test_setback_basic(self):
        a = datetime.datetime(2014, 1, 1, 0, 0, 0, 0)
        b = datetime.datetime(2014, 1, 3, 12, 0, 0, 0)
        #delta = 6 hours
        base = set_up_datetimes(a, b, 21600)

        DAT = copy.deepcopy(base)
        DAT_temp = [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        append_data_to_datetime(DAT, DAT_temp)

        IAT = copy.deepcopy(base)
        IAT_temp = [60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60]
        append_data_to_datetime(IAT, IAT_temp)

        # just the first data point will count as during operational hours
        op_hours = [[0, 1], [3], []]

        test_ele_cost = 10000
        test_area = 5000
        result = setback_non_op(IAT, DAT, op_hours, test_ele_cost, test_area)

        expected = {
            'Problem': "Nighttime thermostat setbacks are not enabled.",
            'Diagnostic': "More than 30 percent of the data indicates that the " + \
                    "building is being conditioned or ventilated normally " + \
                    "during unoccupied hours.",
            'Recommendation': "Program your thermostats to decrease the " + \
                    "heating setpoint, or increase the cooling setpoint during " + \
                    "unoccuppied times.  Additionally, you may have a " + \
                    "contractor configure the RTU to reduce ventilation.",
            'Savings': round(((80-60) * 0.03 * 1 * 0.07 * test_ele_cost * (10/11)), 2)}

        self.assertEqual(result, expected)

    def test_setback_HVAC_success(self):
        a = datetime.datetime(2014, 1, 1, 0, 0, 0, 0)
        b = datetime.datetime(2014, 1, 3, 6, 0, 0, 0)
        #delta = 6 hours
        base = set_up_datetimes(a, b, 21600)

        # copy data to put in the right format
        DAT = copy.deepcopy(base)
        DAT_temp = [10, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        append_data_to_datetime(DAT, DAT_temp)

        IAT = copy.deepcopy(base)
        IAT_temp = [60, 60, 60, 60, 60, 60, 60, 60, 60, 60]
        append_data_to_datetime(IAT, IAT_temp)

        HVAC = copy.deepcopy(base)
        HVAC_temp = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        append_data_to_datetime(HVAC, HVAC_temp)

        # the first point is the only operational point
        op_hours = [[0, 1], [3], []]
        result = setback_non_op(IAT, DAT, op_hours, 10000, 5000, HVAC)

        self.assertEqual(result, {})

    def test_setback_HVAC_basic(self):
        a = datetime.datetime(2014, 1, 1, 0, 0, 0, 0)
        b = datetime.datetime(2014, 1, 3, 12, 0, 0, 0)
        #delta = 6 hours
        base = set_up_datetimes(a, b, 21600)

        DAT = copy.deepcopy(base)
        DAT_temp = [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        append_data_to_datetime(DAT, DAT_temp)

        IAT = copy.deepcopy(base)
        IAT_temp = [60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60]
        append_data_to_datetime(IAT, IAT_temp)

        HVAC = copy.deepcopy(base)
        HVAC_temp = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
        append_data_to_datetime(HVAC, HVAC_temp)

        # just the first data point will count as during operational hours
        op_hours = [[0, 1], [3], []]

        test_ele_cost = 10000
        test_area = 5000
        result = setback_non_op(IAT, DAT, op_hours, test_ele_cost, test_area)

        expected = {
            'Problem': "Nighttime thermostat setbacks are not enabled.",
            'Diagnostic': "More than 30 percent of the data indicates that the " + \
                    "building is being conditioned or ventilated normally " + \
                    "during unoccupied hours.",
            'Recommendation': "Program your thermostats to decrease the " + \
                    "heating setpoint, or increase the cooling setpoint during " + \
                    "unoccuppied times.  Additionally, you may have a " + \
                    "contractor configure the RTU to reduce ventilation.",
            'Savings': round(((80-60) * 0.03 * 1 * 0.07 * test_ele_cost * (10/11)), 2)}

        self.assertEqual(result, expected)



