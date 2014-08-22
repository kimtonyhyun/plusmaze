import collections
import ok

from util import *

GateSetting = collections.namedtuple('Gate', 'epaddr cl op')
DoseSetting = collections.namedtuple('Dose', 'trig_bit epaddr dose_vol dose_rep')

class DeviceError(Exception):
    pass

class PlusMaze(object):
    ordered_dirs = ['west', 'north', 'south', 'east']

    BITFILE = 'toplevel.bit'

    # HARDWARE SETTINGS
    #------------------------------------------------------------
    gate_settings = {'north': GateSetting(epaddr=0x03, cl=550, op=1200),
                     'south': GateSetting(epaddr=0x00, cl=585, op=1200),
                     'east' : GateSetting(epaddr=0x01, cl=565, op=1200),
                     'west' : GateSetting(epaddr=0x02, cl=540, op=1200)}

    dose_settings = {'TRIG_EPADDR': 0x40,
                     'REPS_EPADDR': 0x08,
                     'all'  : DoseSetting(trig_bit=0, epaddr=None, dose_vol=None, dose_rep=None),
                     'east' : DoseSetting(trig_bit=1, epaddr=0x04, dose_vol=13500, dose_rep=4),
                     'south': DoseSetting(trig_bit=2, epaddr=0x05, dose_vol=15000, dose_rep=7),
                     'north': DoseSetting(trig_bit=3, epaddr=0x06, dose_vol=15500, dose_rep=5),
                     'west' : DoseSetting(trig_bit=4, epaddr=0x07, dose_vol=16000, dose_rep=4)}

    rotation_settings = {'TRIG_EPADDR': 0x40,
                         'trig_map': {'center ccw': 5,
                                      'center cw' : 6,
                                      'maze ccw': 15,  # Unimplemented
                                      'maze cw' : 15, # Unimplemented
                                     }
                        }

    prox_settings = {'LASTDETECT_EPADDR': 0x20,
                     'names': {0: 'east',
                               1: 'south',
                               2: 'west',
                               3: 'north'}
                    }

    # CONTINUOUS T-MAZE OPERATION
    #   Description of how to rotate the center platform to accommodate the
    #   path of the mouse. The key ('east', 'north') corresponds to the mouse
    #   moving from east to north, which is a right turn. In this case, we
    #   need to move the T-block counterclockwise
    #------------------------------------------------------------
    pos_to_turn = {('east' , 'north'): 'right',
                   ('north', 'west' ): 'right',
                   ('west' , 'south'): 'right',
                   ('south', 'east' ): 'right',
                   ('east' , 'south'): 'left',
                   ('south', 'west' ): 'left',
                   ('west' , 'north'): 'left',
                   ('north', 'east' ): 'left',
                  }

    turn_compensation = {'right': 'center ccw',
                         'left' : 'center cw',
                        }
    def __init__(self):
        self._initialize_fpga()
        self.setup_dosing()

    def _initialize_fpga(self):
        self.xem = ok.FrontPanel()
        num_devices = self.xem.GetDeviceCount()
        print_msg("Detected {} device{}".format(num_devices,
                                                '' if num_devices==2 else 's'))
        if (num_devices == 0):
            raise DeviceError
        else:
            # FIXME: Always opens the first device
            serial = self.xem.GetDeviceListSerial(0)
            if (self.xem.NoError != self.xem.OpenBySerial(serial)):
                print_msg("FPGA with serial {} could not be opened".format(serial))
                raise DeviceError

            if (self.xem.NoError != self.xem.LoadDefaultPLLConfiguration()):
                print_msg("Unable to set default PLL config")
                raise DeviceError

            if (self.xem.NoError != self.xem.ConfigureFPGA(PlusMaze.BITFILE)):
                print_msg("Failed to load bitfile {}".format(PlusMaze.BITFILE))
                raise DeviceError
            else:
                print_msg("Loaded bitfile {} to {}".format(PlusMaze.BITFILE, serial))

    def setup_dosing(self):
        dose_reps = 0x00
        for d in PlusMaze.ordered_dirs:
            dose_reps += PlusMaze.dose_settings[d].dose_rep << \
                            (4*(PlusMaze.dose_settings[d].trig_bit - 1))
            self.xem.SetWireInValue(PlusMaze.dose_settings[d].epaddr,
                                    PlusMaze.dose_settings[d].dose_vol)
        self.xem.SetWireInValue(PlusMaze.dose_settings['REPS_EPADDR'], dose_reps)
        self.xem.UpdateWireIns()

    def get_last_detected_pos(self):
        self.xem.UpdateWireOuts()
        last_detected_id = self.xem.GetWireOutValue(PlusMaze.prox_settings['LASTDETECT_EPADDR'])
        last_detected_name = PlusMaze.prox_settings['names'][last_detected_id]
        return last_detected_name

    def actuate_gate(self, gate, closed):
        val = PlusMaze.gate_settings[gate].cl if closed else PlusMaze.gate_settings[gate].op
        self.xem.SetWireInValue(PlusMaze.gate_settings[gate].epaddr, val)
        self.xem.UpdateWireIns()
        print_msg("{} gate {}".format(gate, "closed" if closed else "opened"))

    def dose(self, d):
        self.xem.ActivateTriggerIn(PlusMaze.dose_settings['TRIG_EPADDR'],
                                   PlusMaze.dose_settings[d].trig_bit)
        print_msg("Dosed {}".format(d))

    def rotate(self, r):
        self.xem.ActivateTriggerIn(PlusMaze.rotation_settings['TRIG_EPADDR'],
                                   PlusMaze.rotation_settings['trig_map'][r])
        print_msg("Rotating {}".format(r))
